"""Tests for the dependency graph: cascade propagation, scope, and probability cap."""

import random
from pathlib import Path

from src.config.loader import build_city
from src.engine.dependencies import _find_dependent_buildings, propagate_cascades
from src.models.event import EventPhase, GameEvent

CONFIG_DIR = Path(__file__).parent.parent.parent / "config"


def _make_cascade_event(
    building_id: str,
    district_id: str,
    tick: int = 0,
    dependency: str = "energy",
) -> GameEvent:
    return GameEvent(
        id="test_cascade_evt",
        template_id="power_outage",
        name="Test Power Outage",
        category="degradation_and_neglect",
        domain="energy",
        phase=EventPhase.DETECTED,
        target_district_id=district_id,
        target_building_id=building_id,
        created_tick=tick,
        detected_tick=tick,
        cascade_dependency=dependency,
        cascade_scope="neighbours",
    )


class TestFindDependentBuildings:
    def test_neighbours_scope_stays_in_district(self):
        _, city = build_city(CONFIG_DIR)
        district = next(iter(city.districts.values()))
        source = next(iter(district.buildings.values()))

        result = _find_dependent_buildings(city, source, "energy", "neighbours")

        for dep in result:
            assert dep.district_id == district.id

    def test_city_scope_is_superset_of_neighbours(self):
        _, city = build_city(CONFIG_DIR)
        district = next(iter(city.districts.values()))
        source = next(iter(district.buildings.values()))

        neighbours = _find_dependent_buildings(city, source, "energy", "neighbours")
        city_wide = _find_dependent_buildings(city, source, "energy", "city")

        assert len(city_wide) >= len(neighbours)

    def test_failed_buildings_excluded(self):
        _, city = build_city(CONFIG_DIR)
        district = next(iter(city.districts.values()))
        buildings = list(district.buildings.values())

        source = buildings[0]
        for b in buildings[1:]:
            b.fail(tick=1, event_id="pre_test")

        result = _find_dependent_buildings(city, source, "energy", "neighbours")
        for dep in result:
            assert not dep.is_failed

    def test_source_building_not_included(self):
        _, city = build_city(CONFIG_DIR)
        district = next(iter(city.districts.values()))
        source = next(iter(district.buildings.values()))

        result = _find_dependent_buildings(city, source, "energy", "neighbours")
        ids = [b.id for b in result]
        assert source.id not in ids


class TestPropagateCascades:
    def test_hidden_events_do_not_cascade(self):
        _, city = build_city(CONFIG_DIR)
        district = next(iter(city.districts.values()))
        building = next(iter(district.buildings.values()))
        building.fail(tick=0, event_id="test_evt")

        event = _make_cascade_event(building.id, district.id, tick=0)
        event.phase = EventPhase.HIDDEN
        city.events.append(event)

        results = propagate_cascades(city, tick=0)
        assert len(results) == 0

    def test_responding_events_do_not_cascade(self):
        """A building under active repair should not cascade failures to neighbours."""
        _, city = build_city(CONFIG_DIR)
        district = next(iter(city.districts.values()))
        building = next(iter(district.buildings.values()))
        building.fail(tick=0, event_id="test_evt")

        event = _make_cascade_event(building.id, district.id, tick=0)
        event.phase = EventPhase.RESPONDING
        city.events.append(event)

        results = propagate_cascades(city, tick=0)
        assert len(results) == 0

    def test_no_cascade_at_mid_day_tick(self):
        """After first detection, cascades only roll at daily boundaries (every 24 ticks)."""
        _, city = build_city(CONFIG_DIR)
        district = next(iter(city.districts.values()))
        building = next(iter(district.buildings.values()))
        building.fail(tick=0, event_id="test_evt")

        event = _make_cascade_event(building.id, district.id, tick=0)
        city.events.append(event)

        # tick=12: hours_since_detected=12, not 0 and not divisible by 24 → skip
        results = propagate_cascades(city, tick=12)
        assert len(results) == 0

    def test_no_cascade_without_dependency_rule(self):
        """Events with no cascade_dependency never propagate."""
        _, city = build_city(CONFIG_DIR)
        district = next(iter(city.districts.values()))
        building = next(iter(district.buildings.values()))
        building.fail(tick=0, event_id="test_evt")

        event = _make_cascade_event(building.id, district.id, tick=0)
        event.cascade_dependency = None
        city.events.append(event)

        results = propagate_cascades(city, tick=0)
        assert len(results) == 0

    def test_cascade_probability_capped_at_0_95(self):
        """Even with extreme multipliers, cascade probability is capped at 0.95 (not 1.0).

        With p=0.95, running 200 independent trials should yield at least one non-cascade.
        P(all 200 cascade) = 0.95^200 ≈ 0.000035.
        """
        # Build once; find a source and an energy-dependent neighbour
        _, city = build_city(CONFIG_DIR)
        source_id = None
        dependent_id = None
        source_district_id = None

        for district_id, district in city.districts.items():
            buildings = list(district.buildings.values())
            for src in buildings:
                for dep in buildings:
                    if dep.id == src.id:
                        continue
                    all_deps = dep.dependencies.critical + dep.dependencies.operational
                    if "energy" in all_deps:
                        source_id = src.id
                        dependent_id = dep.id
                        source_district_id = district_id
                        break
                if source_id:
                    break
            if source_id:
                break

        if source_id is None:
            return  # no energy-dependent building found; skip

        district = city.districts[source_district_id]
        src = district.buildings[source_id]
        dep = district.buildings[dependent_id]

        src.fail(tick=0, event_id="test_evt")
        event = _make_cascade_event(src.id, source_district_id, tick=0)
        event.cascade_risk_boost = 10.0
        city.events.append(event)

        # Run 200 trials: restore dep between each, vary random seed.
        # propagate_cascades does NOT add cascade events to city.events,
        # so only dep.status needs resetting between trials.
        not_cascaded = 0
        for seed in range(200):
            random.seed(seed)
            dep.restore()
            results = propagate_cascades(city, tick=0, cascade_multiplier=100.0)
            if not any(r.target_building_id == dep.id for r in results):
                not_cascaded += 1

        assert not_cascaded > 0, (
            "Cascade probability must be capped at 0.95: all 200 trials cascaded, "
            "which has probability 0.95^200 ≈ 0.000035 if the cap is applied"
        )