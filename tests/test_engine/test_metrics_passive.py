from __future__ import annotations

from pathlib import Path

from src.config.loader import build_city
from src.engine.metrics import apply_passive_dynamics
from src.engine.remedies import apply_remedy
from src.models.event import EventPhase, GameEvent

CONFIG_DIR = Path(__file__).parent.parent.parent / "config"


def _make_event(building_id: str, district_id: str, tick: int = 1) -> GameEvent:
    return GameEvent(
        id="test_evt_passive",
        template_id="pump_failure",
        name="Test Failure",
        category="degradation_and_neglect",
        domain="water",
        phase=EventPhase.DETECTED,
        target_district_id=district_id,
        target_building_id=building_id,
        created_tick=tick,
        detected_tick=tick + 4,
    )


class TestPendingTrustBoostFlush:
    def test_due_boost_applied_and_removed(self):
        cfg, city = build_city(CONFIG_DIR)
        district = city.districts["the_shades"]
        district.pending_trust_boosts.append((100, 5.0, "Test deferred boost"))
        trust_before = district.local_trust.value

        # daily boundary past apply_at=100
        apply_passive_dynamics(city, tick=120, ticks_per_day=24, cfg=cfg)

        assert district.local_trust.value > trust_before
        assert district.pending_trust_boosts == []

    def test_future_boost_not_yet_applied(self):
        cfg, city = build_city(CONFIG_DIR)
        district = city.districts["the_shades"]
        district.pending_trust_boosts.append((500, 5.0, "Future boost"))
        trust_before = district.local_trust.value

        apply_passive_dynamics(city, tick=120, ticks_per_day=24, cfg=cfg)

        assert district.local_trust.value == trust_before
        assert len(district.pending_trust_boosts) == 1


class TestPressStatementScandalHalving:
    def test_scandal_damage_reduced_during_press_statement(self):
        cfg, city = build_city(CONFIG_DIR)
        # Neutralise drift stressors so we can isolate the scandal damage signal
        city.stressors["underinvestment"] = 0.0
        city.stressors["organisational_fragmentation"] = 0.0
        district = city.districts["the_shades"]
        building = next(iter(district.buildings.values()))
        building.fail(tick=1, event_id="test_evt_passive")

        event = _make_event(building.id, district.id, tick=1)
        event.detected_tick = 1
        city.events.append(event)

        baseline_trust = district.local_trust.value
        apply_passive_dynamics(city, tick=48, ticks_per_day=24, cfg=cfg)
        full_scandal_drop = baseline_trust - district.local_trust.value

        # press_statement halves the scandal hit
        cfg, city = build_city(CONFIG_DIR)
        city.stressors["underinvestment"] = 0.0
        city.stressors["organisational_fragmentation"] = 0.0
        district = city.districts["the_shades"]
        building = next(iter(district.buildings.values()))
        building.fail(tick=1, event_id="test_evt_passive")

        event = _make_event(building.id, district.id, tick=1)
        event.detected_tick = 1
        city.events.append(event)

        apply_remedy(cfg, city, event, "press_statement", tick=5)
        trust_after_remedy = district.local_trust.value

        apply_passive_dynamics(city, tick=48, ticks_per_day=24, cfg=cfg)
        muted_scandal_drop = trust_after_remedy - district.local_trust.value

        # roughly half; the inequality modifier scales the muted hit as well
        assert muted_scandal_drop < full_scandal_drop
        assert muted_scandal_drop > 0


class TestStressorDrift:
    def test_neglect_increase_raises_stressor_when_event_ignored(self):
        cfg, city = build_city(CONFIG_DIR)
        district = city.districts["the_shades"]
        building = next(iter(district.buildings.values()))
        building.fail(tick=1, event_id="test_evt_passive")

        event = _make_event(building.id, district.id, tick=1)
        event.detected_tick = 1
        city.events.append(event)

        # just_in_time has neglect_increase: 0.01 in its change_rate
        before = city.stressors["just_in_time"]

        apply_passive_dynamics(city, tick=48, ticks_per_day=24, cfg=cfg)

        assert city.stressors["just_in_time"] > before
        assert abs(city.stressors["just_in_time"] - (before + 0.01)) < 1e-6

    def test_budget_cut_increase_fires_monthly_when_trust_low(self):
        cfg, city = build_city(CONFIG_DIR)
        # underinvestment has budget_cut_increase: 0.05
        city.public_trust.set(20.0, tick=0, cause="test setup")
        before = city.stressors["underinvestment"]

        # monthly boundary
        apply_passive_dynamics(city, tick=720, ticks_per_day=24, cfg=cfg)

        assert city.stressors["underinvestment"] > before
        # no neglected events, so only budget_cut fires
        assert abs(city.stressors["underinvestment"] - (before + 0.05)) < 1e-6

    def test_budget_cut_does_not_fire_when_trust_high(self):
        cfg, city = build_city(CONFIG_DIR)
        city.public_trust.set(80.0, tick=0, cause="test setup")
        before = city.stressors["underinvestment"]

        apply_passive_dynamics(city, tick=720, ticks_per_day=24, cfg=cfg)

        assert city.stressors["underinvestment"] == before
