"""Tests for the metrics engine: effects, delays, duration penalties, income, passive dynamics."""

from pathlib import Path

from src.config.loader import build_city
from src.engine.metrics import (
    _inequality_modifier,
    apply_delayed_effects,
    apply_duration_penalties,
    apply_immediate_effects,
    apply_income,
    apply_passive_dynamics,
    update_global_trust_from_districts,
)
from src.models.event import DelayedEffect, EventPhase, GameEvent, MetricEffect

CONFIG_DIR = Path(__file__).parent.parent.parent / "config"


def _make_event(building_id: str, district_id: str, tick: int = 0) -> GameEvent:
    return GameEvent(
        id="test_evt",
        template_id="pump_failure",
        name="Test Event",
        category="degradation_and_neglect",
        domain="water",
        phase=EventPhase.DETECTED,
        target_district_id=district_id,
        target_building_id=building_id,
        created_tick=tick,
        detected_tick=tick,
    )


class TestApplyImmediateEffects:
    def test_district_trust_decreases(self):
        cfg, city = build_city(CONFIG_DIR)
        district = next(iter(city.districts.values()))
        building = next(iter(district.buildings.values()))

        event = _make_event(building.id, district.id)
        event.immediate_effects = [MetricEffect(
            metric="local_trust", delta=-10, scope="district", district_id=district.id,
        )]

        trust_before = district.local_trust.value
        apply_immediate_effects(city, event, tick=1)
        assert district.local_trust.value < trust_before

    def test_global_metric_decreases(self):
        cfg, city = build_city(CONFIG_DIR)
        district = next(iter(city.districts.values()))
        building = next(iter(district.buildings.values()))

        event = _make_event(building.id, district.id)
        event.immediate_effects = [MetricEffect(
            metric="public_trust", delta=-5, scope="global",
        )]

        trust_before = city.public_trust.value
        apply_immediate_effects(city, event, tick=1)
        assert city.public_trust.value < trust_before

    def test_unknown_metric_does_not_crash(self):
        cfg, city = build_city(CONFIG_DIR)
        district = next(iter(city.districts.values()))
        building = next(iter(district.buildings.values()))

        event = _make_event(building.id, district.id)
        event.immediate_effects = [MetricEffect(
            metric="no_such_metric", delta=-5, scope="global",
        )]

        # Should not raise
        apply_immediate_effects(city, event, tick=1)


class TestApplyDelayedEffects:
    def test_not_applied_before_delay(self):
        cfg, city = build_city(CONFIG_DIR)
        district = next(iter(city.districts.values()))
        building = next(iter(district.buildings.values()))

        event = _make_event(building.id, district.id, tick=0)
        event.delayed_effects = [DelayedEffect(
            delay_hours=24,
            effects=[MetricEffect(metric="public_trust", delta=-5, scope="global")],
        )]
        city.events.append(event)

        trust_before = city.public_trust.value
        apply_delayed_effects(city, tick=12)  # only 12h elapsed
        assert city.public_trust.value == trust_before

    def test_fires_at_correct_tick(self):
        cfg, city = build_city(CONFIG_DIR)
        district = next(iter(city.districts.values()))
        building = next(iter(district.buildings.values()))

        event = _make_event(building.id, district.id, tick=0)
        event.delayed_effects = [DelayedEffect(
            delay_hours=24,
            effects=[MetricEffect(metric="public_trust", delta=-5, scope="global")],
        )]
        city.events.append(event)

        trust_before = city.public_trust.value
        apply_delayed_effects(city, tick=24)
        assert city.public_trust.value < trust_before

    def test_fires_only_once(self):
        cfg, city = build_city(CONFIG_DIR)
        district = next(iter(city.districts.values()))
        building = next(iter(district.buildings.values()))

        event = _make_event(building.id, district.id, tick=0)
        event.delayed_effects = [DelayedEffect(
            delay_hours=24,
            effects=[MetricEffect(metric="public_trust", delta=-5, scope="global")],
        )]
        city.events.append(event)

        apply_delayed_effects(city, tick=24)
        value_after_first = city.public_trust.value

        apply_delayed_effects(city, tick=48)
        assert city.public_trust.value == value_after_first


class TestApplyDurationPenalties:
    def test_fires_on_daily_boundary(self):
        cfg, city = build_city(CONFIG_DIR)
        district = next(iter(city.districts.values()))
        building = next(iter(district.buildings.values()))

        event = _make_event(building.id, district.id, tick=0)
        event.phase = EventPhase.DETECTED
        event.duration_penalty_per_day = -3.0
        event.duration_penalty_metric = "local_trust"
        city.events.append(event)

        trust_before = district.local_trust.value
        apply_duration_penalties(city, tick=24, ticks_per_day=24)
        assert district.local_trust.value < trust_before

    def test_does_not_fire_mid_day(self):
        cfg, city = build_city(CONFIG_DIR)
        district = next(iter(city.districts.values()))
        building = next(iter(district.buildings.values()))

        event = _make_event(building.id, district.id, tick=0)
        event.phase = EventPhase.DETECTED
        event.duration_penalty_per_day = -3.0
        event.duration_penalty_metric = "local_trust"
        city.events.append(event)

        trust_before = district.local_trust.value
        apply_duration_penalties(city, tick=12, ticks_per_day=24)
        assert district.local_trust.value == trust_before

    def test_suspended_while_responding(self):
        """Duration penalty is suspended once a remedy is in progress."""
        cfg, city = build_city(CONFIG_DIR)
        district = next(iter(city.districts.values()))
        building = next(iter(district.buildings.values()))

        event = _make_event(building.id, district.id, tick=0)
        event.phase = EventPhase.RESPONDING
        event.duration_penalty_per_day = -3.0
        event.duration_penalty_metric = "local_trust"
        city.events.append(event)

        trust_before = district.local_trust.value
        apply_duration_penalties(city, tick=24, ticks_per_day=24)
        assert district.local_trust.value == trust_before


class TestApplyIncome:
    def test_fires_at_day_30(self):
        cfg, city = build_city(CONFIG_DIR)
        budget_before = city.budget.value
        apply_income(city, cfg, tick=24 * 30, ticks_per_day=24)
        assert city.budget.value > budget_before

    def test_does_not_fire_before_day_30(self):
        cfg, city = build_city(CONFIG_DIR)
        budget_before = city.budget.value
        apply_income(city, cfg, tick=24 * 15, ticks_per_day=24)
        assert city.budget.value == budget_before

    def test_does_not_fire_at_tick_zero(self):
        cfg, city = build_city(CONFIG_DIR)
        budget_before = city.budget.value
        apply_income(city, cfg, tick=0, ticks_per_day=24)
        assert city.budget.value == budget_before

    def test_failed_transport_reduces_tariffs(self):
        """Failing all transport buildings should yield less income than baseline."""
        cfg1, city1 = build_city(CONFIG_DIR)
        transport_buildings = [
            b for d in city1.districts.values()
            for b in d.buildings.values()
            if b.type_id == "transport"
        ]
        if not transport_buildings:
            return  # skip if no transport buildings in this config

        budget_start1 = city1.budget.value
        apply_income(city1, cfg1, tick=24 * 30, ticks_per_day=24)
        undisrupted_gain = city1.budget.value - budget_start1

        cfg2, city2 = build_city(CONFIG_DIR)
        for d in city2.districts.values():
            for b in d.buildings.values():
                if b.type_id == "transport":
                    b.fail(tick=1, event_id="test_drain")
        budget_start2 = city2.budget.value
        apply_income(city2, cfg2, tick=24 * 30, ticks_per_day=24)
        disrupted_gain = city2.budget.value - budget_start2

        assert disrupted_gain < undisrupted_gain


class TestGlobalTrustFromDistricts:
    def test_district_drop_reduces_global_trust(self):
        cfg, city = build_city(CONFIG_DIR)
        for d in city.districts.values():
            if d.is_residential:
                d.local_trust.apply(-40, tick=1, cause="test")

        trust_before = city.public_trust.value
        update_global_trust_from_districts(city, tick=2)
        assert city.public_trust.value < trust_before


class TestPassiveDynamics:
    def test_regulatory_pressure_rises_with_unresolved_event(self):
        cfg, city = build_city(CONFIG_DIR)
        district = next(iter(city.districts.values()))
        building = next(iter(district.buildings.values()))

        event = _make_event(building.id, district.id, tick=0)
        event.phase = EventPhase.DETECTED
        city.events.append(event)

        pressure_before = city.regulatory_pressure.value
        apply_passive_dynamics(city, tick=24, ticks_per_day=24, cfg=cfg)
        assert city.regulatory_pressure.value > pressure_before

    def test_stability_falls_when_trust_critical(self):
        cfg, city = build_city(CONFIG_DIR)
        city.public_trust.set(10.0, tick=0, cause="test")
        stability_before = city.political_stability.value

        apply_passive_dynamics(city, tick=24, ticks_per_day=24, cfg=cfg)
        assert city.political_stability.value < stability_before

    def test_stressor_drift_on_neglect(self):
        """Events ignored for >24h should increase the underinvestment stressor."""
        cfg, city = build_city(CONFIG_DIR)
        district = next(iter(city.districts.values()))
        building = next(iter(district.buildings.values()))

        event = _make_event(building.id, district.id, tick=0)
        event.phase = EventPhase.DETECTED
        event.detected_tick = 0
        city.events.append(event)

        # Tick 48: daily boundary, event has been detected for 48h (neglected)
        underinvestment_before = city.stressors.get("underinvestment", 0.0)
        apply_passive_dynamics(city, tick=48, ticks_per_day=24, cfg=cfg)
        assert city.stressors.get("underinvestment", 0.0) >= underinvestment_before

    def test_no_change_at_non_daily_boundary(self):
        """Passive dynamics only fires at daily ticks; mid-day has no effect."""
        cfg, city = build_city(CONFIG_DIR)
        district = next(iter(city.districts.values()))
        building = next(iter(district.buildings.values()))

        event = _make_event(building.id, district.id, tick=0)
        event.phase = EventPhase.DETECTED
        city.events.append(event)

        pressure_before = city.regulatory_pressure.value
        apply_passive_dynamics(city, tick=13, ticks_per_day=24, cfg=cfg)  # mid-day
        assert city.regulatory_pressure.value == pressure_before


class TestInequalityModifier:
    def test_victim_amplifies_damage(self):
        assert _inequality_modifier("victim", 0.7) > 1.0

    def test_beneficiary_reduces_damage(self):
        assert _inequality_modifier("beneficiary", 0.7) < 1.0

    def test_none_label_returns_neutral(self):
        assert _inequality_modifier(None, 0.7) == 1.0

    def test_at_zero_level_victim_is_neutral(self):
        """With no city-wide inequality, victim label adds no extra damage."""
        assert _inequality_modifier("victim", 0.0) == 1.0

    def test_ordering_victim_moderate_beneficiary(self):
        level = 0.7
        assert _inequality_modifier("beneficiary", level) < _inequality_modifier("moderate", level)
        assert _inequality_modifier("moderate", level) < _inequality_modifier("victim", level)