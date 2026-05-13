"""Tests for the Phase 3 stressor wirings: just_in_time buffer reduction and
vendor_monoculture multi-district duplication.
"""

from __future__ import annotations

import random
from pathlib import Path

from src.config.loader import build_city
from src.engine.events import (
    _just_in_time_buffer_reduction,
    _vendor_monoculture_duplicates,
    generate_events,
)

CONFIG_DIR = Path(__file__).parent.parent.parent / "config"


class TestJustInTimeBuffer:
    def test_full_stressor_subtracts_full_day_per_buffer_day(self):
        cfg, city = build_city(CONFIG_DIR)
        city.stressors["just_in_time"] = 1.0
        # shortens_buffer_days=1 → 24 hours reduction at full stressor
        assert _just_in_time_buffer_reduction(cfg, city) == 24

    def test_half_stressor_halves_reduction(self):
        cfg, city = build_city(CONFIG_DIR)
        city.stressors["just_in_time"] = 0.5
        assert _just_in_time_buffer_reduction(cfg, city) == 12

    def test_zero_stressor_returns_zero(self):
        cfg, city = build_city(CONFIG_DIR)
        city.stressors["just_in_time"] = 0.0
        assert _just_in_time_buffer_reduction(cfg, city) == 0

    def test_missing_stressor_config_returns_zero(self):
        cfg, city = build_city(CONFIG_DIR)
        cfg.stressors.pop("just_in_time", None)
        city.stressors["just_in_time"] = 1.0
        assert _just_in_time_buffer_reduction(cfg, city) == 0

    def test_generated_event_delay_reduced(self):
        """End-to-end: generate an event under high just_in_time and confirm
        its delayed_effect is shortened relative to the template."""
        cfg, city = build_city(CONFIG_DIR)
        city.stressors["just_in_time"] = 1.0
        # Disable all templates, then enable one that has delayed effects with >= 24h delay.
        target = None
        for t in cfg.event_templates:
            if t.delayed_effects and any(de.delay_hours >= 24 for de in t.delayed_effects):
                target = t
                break
        assert target is not None
        template_delay = target.delayed_effects[0].delay_hours
        for t in cfg.event_templates:
            t.probability_base = 0.0
        target.probability_base = 1.0

        # Try several seeds; assert that at least one generated event has reduced delay
        seen_reduced = False
        for seed in range(20):
            random.seed(seed)
            cfg2, city2 = build_city(CONFIG_DIR)
            city2.stressors["just_in_time"] = 1.0
            for t in cfg2.event_templates:
                t.probability_base = 0.0
            for t in cfg2.event_templates:
                if t.id == target.id:
                    t.probability_base = 1.0
                    break

            new = generate_events(cfg2, city2, tick=10)
            for ev in new:
                if ev.template_id == target.id and ev.delayed_effects:
                    assert ev.delayed_effects[0].delay_hours == max(0, template_delay - 24)
                    seen_reduced = True
                    break
            if seen_reduced:
                break

        assert seen_reduced, "No event with the target template fired across 20 seeds"


class TestVendorMonoculture:
    def test_duplicate_check_returns_true_for_supply_chain_under_high_monoculture(self):
        cfg, city = build_city(CONFIG_DIR)
        city.stressors["vendor_monoculture"] = 1.0
        target = next(t for t in cfg.event_templates if t.category == "supply_chain_failure")

        # With level=1.0 and probability=0.5, half of seeds should return True.
        random.seed(0)
        outcomes = [_vendor_monoculture_duplicates(cfg, city, target) for _ in range(20)]
        assert any(outcomes), "Duplicate check never fired over 20 trials at full stressor"

    def test_duplicate_check_false_for_non_supply_chain(self):
        cfg, city = build_city(CONFIG_DIR)
        city.stressors["vendor_monoculture"] = 1.0
        target = next(
            t for t in cfg.event_templates
            if t.category == "degradation_and_neglect" and not t.residential_impact
        )

        random.seed(0)
        outcomes = [_vendor_monoculture_duplicates(cfg, city, target) for _ in range(20)]
        assert not any(outcomes)

    def test_zero_stressor_never_duplicates(self):
        cfg, city = build_city(CONFIG_DIR)
        city.stressors["vendor_monoculture"] = 0.0
        target = next(t for t in cfg.event_templates if t.category == "supply_chain_failure")

        random.seed(0)
        outcomes = [_vendor_monoculture_duplicates(cfg, city, target) for _ in range(20)]
        assert not any(outcomes)

    def test_multi_district_template_can_produce_two_events(self):
        """End-to-end: when vendor_monoculture is high and a supply-chain template
        targets a building type present in multiple districts, generate_events can
        produce two events from one template tick."""
        cfg, city = build_city(CONFIG_DIR)
        city.stressors["vendor_monoculture"] = 1.0
        # food_supply exists in merchant_quarter, small_gods, river_ankh (3 districts)
        target = next(t for t in cfg.event_templates if t.id == "food_supply_disruption")
        for t in cfg.event_templates:
            t.probability_base = 0.0
        target.probability_base = 1.0

        duplication_seen = False
        for seed in range(50):
            random.seed(seed)
            cfg2, city2 = build_city(CONFIG_DIR)
            city2.stressors["vendor_monoculture"] = 1.0
            for t in cfg2.event_templates:
                t.probability_base = 0.0
            for t in cfg2.event_templates:
                if t.id == target.id:
                    t.probability_base = 1.0
                    break

            new = generate_events(cfg2, city2, tick=10)
            same_template = [e for e in new if e.template_id == target.id]
            if len(same_template) >= 2:
                duplication_seen = True
                break

        assert duplication_seen, "Multi-district duplication never fired in 50 trials"
