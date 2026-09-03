from __future__ import annotations

from src.models.building import Building, BuildingStatus
from src.models.city import City
from src.models.district import District
from src.models.event import EventPhase, GameEvent
from src.models.metric import Metric


def _building(bid: str, district: str, status: BuildingStatus = BuildingStatus.OPERATIONAL) -> Building:
    return Building(id=bid, name=bid, type_id="tavern", district_id=district, position=(0, 0), status=status)


def _city() -> City:
    city = City()
    shades = District(id="shades", name="Shades")
    shades.buildings = {
        "a": _building("a", "shades", BuildingStatus.FAILED),
        "b": _building("b", "shades", BuildingStatus.DEGRADED),
        "c": _building("c", "shades"),
    }
    hill = District(id="hill", name="Hill")
    hill.buildings = {"d": _building("d", "hill"), "e": _building("e", "hill", BuildingStatus.FAILED)}
    city.districts = {"shades": shades, "hill": hill}
    return city


class TestDistrictCounts:
    def test_status_counts(self):
        shades = _city().districts["shades"]
        assert shades.failed_building_count == 1
        assert shades.degraded_building_count == 1
        assert shades.operational_building_count == 1
        assert [b.id for b in shades.failed_buildings] == ["a"]

    def test_crisis_needs_more_than_half_failed(self):
        city = _city()
        assert not city.districts["shades"].is_in_crisis
        city.districts["shades"].buildings["c"].fail(1, "x")
        assert city.districts["shades"].is_in_crisis
        assert District(id="empty", name="Empty").is_in_crisis is False

    def test_active_event_count_follows_active_event_id(self):
        shades = _city().districts["shades"]
        assert shades.active_event_count == 0
        shades.buildings["a"].fail(1, "evt")
        assert shades.active_event_count == 1


class TestCityViews:
    def test_health_and_lookups(self):
        city = _city()
        assert city.infrastructure_health_pct == 40.0
        assert city.districts_in_crisis == 0  # one of two, and one of three, are not more than half
        city.districts["hill"].buildings["d"].fail(1, "x")
        assert city.districts_in_crisis == 1
        assert city.get_building("e").district_id == "hill"
        assert city.get_district_for_building("a").id == "shades"
        assert city.get_building("nope") is None
        assert city.get_metric("budget") is city.budget
        assert city.get_metric("nope") is None

    def test_watch_coverage_counts_security_buildings_only(self):
        city = _city()
        assert city.watch_coverage_pct == 100.0
        post = _building("post", "shades")
        post.type_id = "security"
        city.districts["shades"].buildings["post"] = post
        assert city.watch_coverage_pct == 100.0
        post.fail(1, "x")
        assert city.watch_coverage_pct == 0.0

    def test_event_views(self):
        city = _city()
        hidden = GameEvent(id="h", template_id="t", name="h", category="c", domain="water")
        seen = GameEvent(id="s", template_id="t", name="s", category="c", domain="water", phase=EventPhase.DETECTED)
        done = GameEvent(id="d", template_id="t", name="d", category="c", domain="water", phase=EventPhase.RESOLVED)
        city.events = [hidden, seen, done]
        assert [e.id for e in city.active_events] == ["h", "s"]
        assert [e.id for e in city.visible_events] == ["s"]


class TestMetricTrend:
    def test_trend_over_last_five_snapshots(self):
        m = Metric("m", 50.0)
        assert m.recent_trend == 0.0
        for tick, delta in enumerate((-1, -1, -1, -1, -1, +5), start=1):
            m.apply(delta, tick)
        # last five snapshots run 48, 47, 46, 45, 50: a rise of 2 over four steps
        assert m.recent_trend == 0.5

    def test_unchanged_apply_records_nothing(self):
        m = Metric("m", 0.0, min_value=0.0)
        m.apply(-5, 1)
        assert m.history == []
