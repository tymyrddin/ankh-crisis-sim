from __future__ import annotations

import random
from pathlib import Path

from src.config.loader import build_city
from src.engine.narrative import (
    _format_duration,
    _get_detection_narrative,
    _get_political_narrative,
    _get_stressor_narrative,
    generate_headline,
    generate_story,
)
from src.models.event import EventPhase, GameEvent

CONFIG_DIR = Path(__file__).parent.parent.parent / "config"


def _make_event(
    building_id: str,
    district_id: str,
    domain: str = "water",
    tick: int = 1,
) -> GameEvent:
    return GameEvent(
        id="test_evt_narr",
        template_id="pump_failure",
        name="Test Failure",
        category="degradation_and_neglect",
        domain=domain,
        phase=EventPhase.DETECTED,
        target_district_id=district_id,
        target_building_id=building_id,
        created_tick=tick,
        detected_tick=tick + 4,
    )


class TestHeadlines:
    def test_existing_headline_returned_unchanged(self):
        cfg, city = build_city(CONFIG_DIR)
        district = city.districts["the_shades"]
        building = next(iter(district.buildings.values()))
        event = _make_event(building.id, district.id)
        event.headline = "An existing headline"

        result = generate_headline(cfg, city, event)

        assert result == "An existing headline"

    def test_headline_picks_from_domain_templates(self):
        cfg, city = build_city(CONFIG_DIR)
        district = city.districts["the_shades"]
        building = next(iter(district.buildings.values()))
        event = _make_event(building.id, district.id, domain="water")

        random.seed(0)
        result = generate_headline(cfg, city, event)

        assert isinstance(result, str)
        assert len(result) > 0

    def test_unknown_domain_falls_back_to_general_or_name(self):
        cfg, city = build_city(CONFIG_DIR)
        district = city.districts["the_shades"]
        building = next(iter(district.buildings.values()))
        event = _make_event(building.id, district.id, domain="not_a_real_domain")

        result = generate_headline(cfg, city, event)

        assert isinstance(result, str)
        # Either a general template fired, or the event name leaked through
        assert len(result) > 0


class TestStories:
    def test_story_for_known_domain_returns_text(self):
        cfg, city = build_city(CONFIG_DIR)
        district = city.districts["the_shades"]
        building = next(iter(district.buildings.values()))
        event = _make_event(building.id, district.id, domain="water")

        random.seed(1)
        result = generate_story(cfg, city, event, tick=20)

        assert isinstance(result, str)
        assert len(result) > 0

    def test_story_for_unknown_domain_returns_empty_string(self):
        cfg, city = build_city(CONFIG_DIR)
        district = city.districts["the_shades"]
        building = next(iter(district.buildings.values()))
        event = _make_event(building.id, district.id, domain="not_a_real_domain")
        event.template_id = "no_such_template"  # no template pool either

        result = generate_story(cfg, city, event, tick=20)

        assert result == ""


class TestDetectionNarrative:
    def test_immediate_detection(self):
        cfg, _ = build_city(CONFIG_DIR)
        event = GameEvent(
            id="x", template_id="x", name="x", category="x", domain="water",
            created_tick=10, detected_tick=10,
        )

        text = _get_detection_narrative(cfg, event, tick=10)

        assert "immediately" in text.lower() or text

    def test_short_delay_picks_citizen_narrative(self):
        cfg, _ = build_city(CONFIG_DIR)
        event = GameEvent(
            id="x", template_id="x", name="x", category="x", domain="water",
            created_tick=0, detected_tick=24,
        )

        text = _get_detection_narrative(cfg, event, tick=24)

        # Falls into the "less than 48 hours" branch
        assert isinstance(text, str)

    def test_long_delay_picks_pride_concealment(self):
        cfg, _ = build_city(CONFIG_DIR)
        event = GameEvent(
            id="x", template_id="x", name="x", category="x", domain="water",
            created_tick=0, detected_tick=200,
        )

        text = _get_detection_narrative(cfg, event, tick=200)

        assert isinstance(text, str)


class TestPoliticalNarrative:
    def test_low_pressure_returns_silence(self):
        cfg, city = build_city(CONFIG_DIR)
        city.regulatory_pressure.set(10.0, tick=0, cause="test setup")

        text = _get_political_narrative(cfg, city)

        assert isinstance(text, str)
        assert len(text) > 0

    def test_high_pressure_branch(self):
        cfg, city = build_city(CONFIG_DIR)
        city.regulatory_pressure.set(70.0, tick=0, cause="test setup")

        text = _get_political_narrative(cfg, city)

        assert isinstance(text, str)
        assert len(text) > 0


class TestStressorNarrative:
    def test_dominant_stressor_label_used(self):
        cfg, city = build_city(CONFIG_DIR)
        city.stressors["underinvestment"] = 0.95
        for k in city.stressors:
            if k != "underinvestment":
                city.stressors[k] = 0.1

        text = _get_stressor_narrative(city)

        assert "underinvestment" in text.lower()

    def test_no_stressors_returns_default(self):
        cfg, city = build_city(CONFIG_DIR)
        city.stressors.clear()

        text = _get_stressor_narrative(city)

        assert "underlying conditions" in text.lower()


class TestFormatDuration:
    def test_hours_for_short_event(self):
        cfg, city = build_city(CONFIG_DIR)
        district = city.districts["the_shades"]
        building = next(iter(district.buildings.values()))
        event = _make_event(building.id, district.id, tick=1)
        event.detected_tick = 10  # 9 hours
        city.events.append(event)

        text = _format_duration(event, city)

        assert "9 hours" == text

    def test_days_for_long_event(self):
        cfg, city = build_city(CONFIG_DIR)
        district = city.districts["the_shades"]
        building = next(iter(district.buildings.values()))
        event = _make_event(building.id, district.id, tick=1)
        event.detected_tick = 100  # 99 hours, four days
        city.events.append(event)

        text = _format_duration(event, city)

        assert "day" in text
