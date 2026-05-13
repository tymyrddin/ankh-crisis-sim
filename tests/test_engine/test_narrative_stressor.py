"""Tests for the narrative_effects stressor: accumulator + shaped display value."""

from __future__ import annotations

import math
from pathlib import Path

from src.config.loader import build_city
from src.engine.metrics import (
    apply_passive_dynamics,
    increment_narrative_effects,
    narrative_effects_shaped,
)
from src.engine.remedies import apply_remedy, process_remedy_completions
from src.models.event import EventPhase, GameEvent

CONFIG_DIR = Path(__file__).parent.parent.parent / "config"


def _make_event(building_id: str, district_id: str, tick: int = 1) -> GameEvent:
    return GameEvent(
        id="test_evt_ne",
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


class TestShape:
    def test_zero_raw_returns_zero(self):
        assert narrative_effects_shaped(0.0) == 0.0

    def test_negative_raw_returns_zero(self):
        assert narrative_effects_shaped(-1.0) == 0.0

    def test_tanh_shape_matches_math(self):
        assert abs(narrative_effects_shaped(1.0, "tanh") - math.tanh(1.0)) < 1e-9

    def test_unbounded_raw_caps_at_one(self):
        assert narrative_effects_shaped(100.0, "tanh") <= 1.0
        assert narrative_effects_shaped(100.0, "tanh") > 0.99


class TestAccumulator:
    def test_press_statement_application_raises_counter(self):
        cfg, city = build_city(CONFIG_DIR)
        city.stressors["narrative_effects"] = 0.0
        district = city.districts["the_shades"]
        building = next(iter(district.buildings.values()))
        building.fail(tick=1, event_id="test_evt_ne")

        event = _make_event(building.id, district.id)
        city.events.append(event)

        apply_remedy(cfg, city, event, "press_statement", tick=10)

        # press_statement_increment = 0.05
        assert city.stressors["narrative_effects"] > 0.0
        assert abs(city.stressors["narrative_effects"] - 0.05) < 1e-6

    def test_contradicts_raises_counter_more_than_press_statement(self):
        cfg, city = build_city(CONFIG_DIR)
        city.stressors["narrative_effects"] = 0.0
        city.stressors["underinvestment"] = 0.0
        city.stressors["organisational_fragmentation"] = 0.0
        district = city.districts["the_shades"]
        building = next(iter(district.buildings.values()))
        building.fail(tick=1, event_id="test_evt_ne")

        event = _make_event(building.id, district.id)
        city.events.append(event)

        apply_remedy(cfg, city, event, "press_statement", tick=10)
        # After apply: counter = 0.05 (press_statement increment)
        before_contradicts = city.stressors["narrative_effects"]

        # Let the 48h window close without action
        process_remedy_completions(cfg, city, tick=60)

        # Contradicts increment = 0.10
        assert city.stressors["narrative_effects"] > before_contradicts
        assert abs(city.stressors["narrative_effects"] - (before_contradicts + 0.10)) < 1e-6

    def test_helper_no_op_when_stressor_missing_from_cfg(self):
        cfg, city = build_city(CONFIG_DIR)
        # Strip the stressor config; the helper should be tolerant
        cfg.stressors.pop("narrative_effects", None)
        city.stressors["narrative_effects"] = 0.0

        increment_narrative_effects(city, cfg, "press_statement")

        assert city.stressors["narrative_effects"] == 0.0

    def test_unknown_increment_key_is_zero(self):
        cfg, city = build_city(CONFIG_DIR)
        city.stressors["narrative_effects"] = 0.0

        increment_narrative_effects(city, cfg, "no_such_key")

        assert city.stressors["narrative_effects"] == 0.0


class TestTrustDecayAmplifier:
    def test_high_narrative_effects_amplifies_scandal_damage(self):
        """Scandal damage with high narrative_effects must exceed scandal damage at zero."""
        cfg, city = build_city(CONFIG_DIR)
        # Neutralise drift stressors and the inequality amplifier
        city.stressors["underinvestment"] = 0.0
        city.stressors["organisational_fragmentation"] = 0.0
        city.stressors["narrative_effects"] = 0.0

        district = city.districts["the_shades"]
        building = next(iter(district.buildings.values()))
        building.fail(tick=1, event_id="test_evt_ne")
        event = _make_event(building.id, district.id, tick=1)
        event.detected_tick = 1
        city.events.append(event)

        baseline_trust = district.local_trust.value
        apply_passive_dynamics(city, tick=48, ticks_per_day=24, cfg=cfg)
        zero_damage = baseline_trust - district.local_trust.value

        # Reset and run with high narrative_effects
        cfg, city = build_city(CONFIG_DIR)
        city.stressors["underinvestment"] = 0.0
        city.stressors["organisational_fragmentation"] = 0.0
        city.stressors["narrative_effects"] = 5.0  # tanh(5) is essentially 1

        district = city.districts["the_shades"]
        building = next(iter(district.buildings.values()))
        building.fail(tick=1, event_id="test_evt_ne")
        event = _make_event(building.id, district.id, tick=1)
        event.detected_tick = 1
        city.events.append(event)

        baseline_trust = district.local_trust.value
        apply_passive_dynamics(city, tick=48, ticks_per_day=24, cfg=cfg)
        amplified_damage = baseline_trust - district.local_trust.value

        assert amplified_damage > zero_damage


class TestCityDisplayProperty:
    def test_display_property_returns_shaped_value(self):
        cfg, city = build_city(CONFIG_DIR)
        city.stressors["narrative_effects"] = 1.0
        assert abs(city.narrative_effects_display - math.tanh(1.0)) < 1e-9

    def test_display_property_zero_when_counter_zero(self):
        cfg, city = build_city(CONFIG_DIR)
        city.stressors["narrative_effects"] = 0.0
        assert city.narrative_effects_display == 0.0
