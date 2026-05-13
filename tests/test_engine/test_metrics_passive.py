"""Tests for passive metric dynamics: pending trust boost flush, press-statement scandal
halving, stressor drift via neglect_increase and budget_cut_increase.

Closes coverage gaps around src/engine/metrics.py:268-272 and 283-295.
"""

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

        # Tick 120 is a daily boundary (ticks_per_day=24), past the scheduled apply_at=100
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
        # Detected long enough ago to trigger scandal escalation (> 1 day)
        event.detected_tick = 1
        city.events.append(event)

        # Snapshot trust without any remedy: ordinary scandal at full strength
        baseline_trust = district.local_trust.value
        apply_passive_dynamics(city, tick=48, ticks_per_day=24, cfg=cfg)
        full_scandal_drop = baseline_trust - district.local_trust.value

        # Reset and apply press_statement: scandal damage should be halved
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

        # The muted version is roughly half (multiplier is 0.5).
        # Tolerate the inequality modifier amplifying the muted hit too.
        assert muted_scandal_drop < full_scandal_drop
        assert muted_scandal_drop > 0


class TestStressorDrift:
    def test_neglect_increase_raises_stressor_when_event_ignored(self):
        cfg, city = build_city(CONFIG_DIR)
        district = city.districts["the_shades"]
        building = next(iter(district.buildings.values()))
        building.fail(tick=1, event_id="test_evt_passive")

        event = _make_event(building.id, district.id, tick=1)
        event.detected_tick = 1  # ignored from tick 1 onwards
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

        # 30 days * 24 ticks = 720. apply_passive_dynamics needs a monthly boundary.
        apply_passive_dynamics(city, tick=720, ticks_per_day=24, cfg=cfg)

        assert city.stressors["underinvestment"] > before
        # 0.05 from monthly budget_cut + 0.01 neglect_increase if any neglected events;
        # there are none here, so only budget_cut fires
        assert abs(city.stressors["underinvestment"] - (before + 0.05)) < 1e-6

    def test_budget_cut_does_not_fire_when_trust_high(self):
        cfg, city = build_city(CONFIG_DIR)
        city.public_trust.set(80.0, tick=0, cause="test setup")
        before = city.stressors["underinvestment"]

        apply_passive_dynamics(city, tick=720, ticks_per_day=24, cfg=cfg)

        assert city.stressors["underinvestment"] == before
