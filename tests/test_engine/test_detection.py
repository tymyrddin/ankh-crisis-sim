"""Tests for the detection system: timing, caching, and discovery speed multiplier."""

from pathlib import Path

from src.config.loader import build_city
from src.engine.detection import process_detection
from src.models.event import EventPhase, GameEvent

CONFIG_DIR = Path(__file__).parent.parent.parent / "config"


def _make_hidden_event(
    building_id: str,
    district_id: str,
    tick: int = 0,
    domain: str = "water",
) -> GameEvent:
    return GameEvent(
        id="test_hidden_evt",
        template_id="pump_failure",
        name="Test Hidden Event",
        category="degradation_and_neglect",
        domain=domain,
        phase=EventPhase.HIDDEN,
        target_district_id=district_id,
        target_building_id=building_id,
        created_tick=tick,
    )


class TestProcessDetection:
    def test_hidden_event_not_detected_early(self):
        """An event with a very long discovery time should not be detected at tick 0."""
        cfg, city = build_city(CONFIG_DIR)
        district = next(iter(city.districts.values()))
        building = next(iter(district.buildings.values()))
        building.fail(tick=0, event_id="test_hidden_evt")
        building.hidden_failure = True

        event = _make_hidden_event(building.id, district.id, tick=0)
        event.discovery_time_hours = 999.0  # pre-set to skip random roll
        city.events.append(event)

        detected = process_detection(cfg, city, tick=0)
        assert len(detected) == 0
        assert event.phase == EventPhase.HIDDEN

    def test_hidden_event_detected_after_elapsed_time(self):
        """An event with discovery_time_hours=5 should be detected by tick 5."""
        cfg, city = build_city(CONFIG_DIR)
        district = next(iter(city.districts.values()))
        building = next(iter(district.buildings.values()))
        building.fail(tick=0, event_id="test_hidden_evt")
        building.hidden_failure = True

        event = _make_hidden_event(building.id, district.id, tick=0)
        event.discovery_time_hours = 5.0  # pre-set; skip random roll
        city.events.append(event)

        detected = process_detection(cfg, city, tick=5)
        assert len(detected) == 1
        assert event.phase == EventPhase.DETECTED
        assert event.detected_tick == 5

    def test_building_hidden_flag_cleared_on_detection(self):
        """When an event is detected, building.hidden_failure is cleared."""
        cfg, city = build_city(CONFIG_DIR)
        district = next(iter(city.districts.values()))
        building = next(iter(district.buildings.values()))
        building.fail(tick=0, event_id="test_hidden_evt")
        building.hidden_failure = True

        event = _make_hidden_event(building.id, district.id, tick=0)
        event.discovery_time_hours = 1.0
        city.events.append(event)

        process_detection(cfg, city, tick=1)
        assert not building.hidden_failure

    def test_already_detected_event_not_reprocessed(self):
        """Events that are already visible should never appear in detection output."""
        cfg, city = build_city(CONFIG_DIR)
        district = next(iter(city.districts.values()))
        building = next(iter(district.buildings.values()))
        building.fail(tick=0, event_id="test_hidden_evt")

        event = _make_hidden_event(building.id, district.id, tick=0)
        event.phase = EventPhase.DETECTED  # already visible
        event.discovery_time_hours = 1.0
        city.events.append(event)

        detected = process_detection(cfg, city, tick=1)
        assert len(detected) == 0

    def test_resolved_event_not_reprocessed(self):
        """RESOLVED events are inactive and should not go through detection."""
        cfg, city = build_city(CONFIG_DIR)
        district = next(iter(city.districts.values()))
        building = next(iter(district.buildings.values()))

        event = _make_hidden_event(building.id, district.id, tick=0)
        event.phase = EventPhase.RESOLVED
        event.discovery_time_hours = 1.0
        city.events.append(event)

        detected = process_detection(cfg, city, tick=1)
        assert len(detected) == 0


class TestDiscoveryTimeCaching:
    def test_discovery_time_cached_after_first_check(self):
        """process_detection should set discovery_time_hours on the first call."""
        cfg, city = build_city(CONFIG_DIR)
        district = next(iter(city.districts.values()))
        building = next(iter(district.buildings.values()))
        building.fail(tick=0, event_id="test_hidden_evt")
        building.hidden_failure = True

        event = _make_hidden_event(building.id, district.id, tick=0)
        assert event.discovery_time_hours is None

        city.events.append(event)
        process_detection(cfg, city, tick=0)

        assert event.discovery_time_hours is not None

    def test_cached_value_not_recalculated(self):
        """Once cached, discovery_time_hours must not change on subsequent calls."""
        cfg, city = build_city(CONFIG_DIR)
        district = next(iter(city.districts.values()))
        building = next(iter(district.buildings.values()))
        building.fail(tick=0, event_id="test_hidden_evt")
        building.hidden_failure = True

        event = _make_hidden_event(building.id, district.id, tick=0)
        city.events.append(event)

        process_detection(cfg, city, tick=0)
        cached_time = event.discovery_time_hours

        # Change the district's range; this must not affect the cached value
        district.discovery_time_hours = (1000.0, 2000.0)
        process_detection(cfg, city, tick=1)

        assert event.discovery_time_hours == cached_time


class TestDiscoverySpeedMultiplier:
    def test_lower_multiplier_yields_shorter_discovery_time(self):
        """discovery_speed_multiplier < 1 makes events surface faster.

        Uses domain="" to avoid incident_type_discovery overrides, and a large
        multiplier gap (0.001 vs 1000) so the ranges never overlap regardless
        of the random base time drawn from the district's [low, high] range.
        """
        cfg1, city1 = build_city(CONFIG_DIR)
        district1 = city1.districts.get("the_shades") or next(iter(city1.districts.values()))
        building1 = next(iter(district1.buildings.values()))
        building1.fail(tick=0, event_id="test_hidden_evt")
        building1.hidden_failure = True

        cfg1.settings.discovery_speed_multiplier = 0.001  # discover almost immediately
        event1 = _make_hidden_event(building1.id, district1.id, tick=0, domain="")
        city1.events.append(event1)
        process_detection(cfg1, city1, tick=0)  # triggers caching
        fast_time = event1.discovery_time_hours

        cfg2, city2 = build_city(CONFIG_DIR)
        district2 = city2.districts.get("the_shades") or next(iter(city2.districts.values()))
        building2 = next(iter(district2.buildings.values()))
        building2.fail(tick=0, event_id="test_hidden_evt")
        building2.hidden_failure = True

        cfg2.settings.discovery_speed_multiplier = 1000.0  # extremely slow discovery
        event2 = _make_hidden_event(building2.id, district2.id, tick=0, domain="")
        city2.events.append(event2)
        process_detection(cfg2, city2, tick=0)  # triggers caching
        slow_time = event2.discovery_time_hours

        assert fast_time < slow_time