import random
from pathlib import Path

import pytest

from src.config.loader import EventTemplate, build_city
from src.engine.events import _calculate_probability, _find_target_building, generate_events
from src.models.event import EventPhase

CONFIG_DIR = Path(__file__).parent.parent.parent / "config"


class TestCalculateProbability:
    def test_higher_stressor_level_increases_probability(self):
        cfg, city = build_city(CONFIG_DIR)
        template = EventTemplate(
            id="test",
            name="Test",
            category="degradation_and_neglect",
            probability_base=0.01,
            stressor_amplifiers={"underinvestment": 3.0},
        )

        city.stressors["underinvestment"] = 0.1
        low_prob = _calculate_probability(template, city, 1.0)

        city.stressors["underinvestment"] = 0.9
        high_prob = _calculate_probability(template, city, 1.0)

        assert high_prob > low_prob

    def test_district_failure_modifier_scales_probability(self):
        cfg, city = build_city(CONFIG_DIR)
        template = EventTemplate(
            id="test",
            name="Test",
            category="degradation_and_neglect",
            probability_base=0.01,
        )

        low_prob = _calculate_probability(template, city, 0.5)
        high_prob = _calculate_probability(template, city, 3.0)

        assert high_prob > low_prob

    def test_probability_capped_at_0_5(self):
        cfg, city = build_city(CONFIG_DIR)
        template = EventTemplate(
            id="test",
            name="Test",
            category="degradation_and_neglect",
            probability_base=0.9,
            stressor_amplifiers={"underinvestment": 10.0},
        )

        city.stressors["underinvestment"] = 1.0
        prob = _calculate_probability(template, city, 5.0)

        assert prob <= 0.5

    def test_district_stressor_label_amplifies_probability(self):
        cfg, city = build_city(CONFIG_DIR)
        template = EventTemplate(
            id="test",
            name="Test",
            category="degradation_and_neglect",
            probability_base=0.01,
            stressor_amplifiers={"underinvestment": 2.0},
        )

        city.stressors["underinvestment"] = 0.5
        base_prob = _calculate_probability(template, city, 1.0)
        amplified_prob = _calculate_probability(
            template, city, 1.0, district_stressors={"underinvestment": "extreme"},
        )

        assert amplified_prob > base_prob

    def test_zero_base_probability_stays_zero(self):
        cfg, city = build_city(CONFIG_DIR)
        template = EventTemplate(
            id="test",
            name="Test",
            category="degradation_and_neglect",
            probability_base=0.0,
        )
        city.stressors["underinvestment"] = 1.0
        prob = _calculate_probability(template, city, 3.0)
        assert prob == 0.0


class TestFindTargetBuilding:
    def test_returns_none_when_no_candidates(self):
        _, city = build_city(CONFIG_DIR)
        district = next(iter(city.districts.values()))

        for b in district.buildings.values():
            b.active_event_id = "occupied"

        template = EventTemplate(id="test", name="Test", category="test")
        result = _find_target_building(template, city, district.id)
        assert result is None

    def test_skips_occupied_buildings(self):
        _, city = build_city(CONFIG_DIR)
        district = next(iter(city.districts.values()))
        buildings = list(district.buildings.values())

        if len(buildings) < 2:
            pytest.skip("needs at least two buildings")

        for b in buildings[:-1]:
            b.active_event_id = "occupied"

        template = EventTemplate(id="test", name="Test", category="test")
        result = _find_target_building(template, city, district.id)

        assert result is not None
        assert result.id == buildings[-1].id

    def test_filters_by_building_type(self):
        _, city = build_city(CONFIG_DIR)
        district = next(iter(city.districts.values()))

        absent_type = "nonexistent_type_xyz"
        template = EventTemplate(
            id="test",
            name="Test",
            category="test",
            target_building_types=[absent_type],
        )
        result = _find_target_building(template, city, district.id)
        assert result is None

    def test_returns_none_for_unknown_district(self):
        _, city = build_city(CONFIG_DIR)
        template = EventTemplate(id="test", name="Test", category="test")
        result = _find_target_building(template, city, "no_such_district")
        assert result is None


class TestGenerateEvents:
    def test_no_events_with_zero_rate_multiplier(self):
        cfg, city = build_city(CONFIG_DIR)
        cfg.settings.event_rate_multiplier = 0.0

        random.seed(42)
        for tick in range(100):
            events = generate_events(cfg, city, tick=tick)
            assert len(events) == 0, f"Event fired at tick {tick} with multiplier=0"

    def test_generated_event_marks_building_failed(self):
        cfg, city = build_city(CONFIG_DIR)
        cfg.settings.event_rate_multiplier = 100.0

        random.seed(1)
        events = []
        for tick in range(50):
            events.extend(generate_events(cfg, city, tick=tick))
            if events:
                break

        if not events:
            pytest.skip("no event rolled even at multiplier 100")

        event = events[0]
        building = city.get_building(event.target_building_id)
        assert building is not None
        assert building.is_failed
        assert building.hidden_failure is True

    def test_generated_event_starts_hidden(self):
        cfg, city = build_city(CONFIG_DIR)
        cfg.settings.event_rate_multiplier = 100.0

        random.seed(2)
        events = []
        for tick in range(50):
            events.extend(generate_events(cfg, city, tick=tick))
            if events:
                break

        if not events:
            return

        assert events[0].phase == EventPhase.HIDDEN

    def test_generated_event_has_correct_district(self):
        cfg, city = build_city(CONFIG_DIR)
        cfg.settings.event_rate_multiplier = 100.0

        random.seed(3)
        events = []
        for tick in range(50):
            events.extend(generate_events(cfg, city, tick=tick))
            if events:
                break

        if not events:
            return

        event = events[0]
        assert event.target_district_id in city.districts
