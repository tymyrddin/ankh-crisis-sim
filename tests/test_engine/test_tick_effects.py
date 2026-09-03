from __future__ import annotations

import random
from pathlib import Path

from src.config.loader import build_city
from src.engine.detection import _get_discovery_time
from src.engine.metrics import apply_duration_penalties
from src.engine.narrative import generate_story
from src.engine.remedies import apply_remedy
from src.engine.simulation import Simulation
from src.models.event import EventPhase, GameEvent

CONFIG_DIR = Path(__file__).parent.parent.parent / "config"


def _event(building, district, **kw) -> GameEvent:
    base = dict(
        id="evt", template_id="pump_failure", name="Failure", category="degradation_and_neglect",
        domain="water", phase=EventPhase.DETECTED, target_district_id=district.id,
        target_building_id=building.id, created_tick=1, detected_tick=1,
    )
    base.update(kw)
    return GameEvent(**base)


class TestCascadeEffects:
    def test_cascade_trust_damage_is_applied(self, monkeypatch):
        sim = Simulation(CONFIG_DIR)
        sim.initialise()
        city, cfg = sim.city, sim.cfg
        cfg.settings.event_rate_multiplier = 0.0
        source = next(b for d in city.districts.values() for b in d.buildings.values() if "water" in b.produces)
        event = _event(source, city.districts[source.district_id], id="root", created_tick=0, detected_tick=0,
                       cascade_dependency="water", cascade_scope="city")
        source.fail(0, "root")
        city.events.append(event)
        monkeypatch.setattr(random, "random", lambda: 0.0)

        for _ in range(24):
            sim.tick()

        cascades = [e for e in city.events if e.id.startswith("cascade_")]
        assert cascades
        assert any(
            s.cause.startswith("Cascade:")
            for d in city.districts.values() for s in d.local_trust.history
        )


class TestDurationPenalty:
    def test_hidden_event_pays_nothing_until_detected(self):
        cfg, city = build_city(CONFIG_DIR)
        district = city.districts["the_shades"]
        building = next(iter(district.buildings.values()))
        event = _event(building, district, phase=EventPhase.HIDDEN, detected_tick=None,
                       created_tick=0, duration_penalty_per_day=-2.0)
        city.events.append(event)
        before = district.local_trust.value

        for tick in range(1, 73):
            apply_duration_penalties(city, tick, 24)
        assert district.local_trust.value == before

        event.detect(72)
        apply_duration_penalties(city, 96, 24)
        assert district.local_trust.value < before


class TestStoriesFromTemplate:
    def test_story_prefers_the_template_pool(self):
        cfg, city = build_city(CONFIG_DIR)
        template = next(t for t in cfg.event_templates if t.stories)
        district = next(iter(city.districts.values()))
        building = next(iter(district.buildings.values()))
        event = _event(building, district, template_id=template.id, domain=template.domain)

        story = generate_story(cfg, city, event, tick=5)

        # match on the text before the first placeholder
        openings = [s.split("{")[0] for s in template.stories]
        assert any(story.startswith(o) for o in openings if o)


class TestDoubleResponse:
    def test_second_remedy_refused_while_responding(self):
        cfg, city = build_city(CONFIG_DIR)
        district = city.districts["the_shades"]
        building = next(iter(district.buildings.values()))
        building.fail(1, "evt")
        event = _event(building, district)
        city.events.append(event)

        assert apply_remedy(cfg, city, event, "technical_restoration", tick=10).success
        budget = city.budget.value
        second = apply_remedy(cfg, city, event, "resilience_investment", tick=11)
        assert not second.success
        assert city.budget.value == budget


class TestDiscoveryInputs:
    def test_building_modifier_comes_from_types_and_instance_override(self):
        cfg, city = build_city(CONFIG_DIR)
        palace = next(b for d in city.districts.values() for b in d.buildings.values() if b.type_id == "palace")
        assert palace.detection_time_modifier == cfg.building_types["palace"].detection_time_modifier
        overridden = [b for d in city.districts.values() for b in d.buildings.values()
                      if b.detection_time_modifier != cfg.building_types[b.type_id].detection_time_modifier]
        assert overridden, "instances.yml declares per-building overrides"

    def test_template_range_replaces_district_range(self):
        cfg, city = build_city(CONFIG_DIR)
        fire = cfg.template("workshop_fire")
        assert fire is not None and fire.discovery_hours == (0.0, 2.0)
        workshop = next(b for d in city.districts.values() for b in d.buildings.values() if b.type_id == "workshop")
        district = city.districts[workshop.district_id]
        event = _event(workshop, district, template_id="workshop_fire", phase=EventPhase.HIDDEN,
                       detected_tick=None, domain="public_services")

        hours = _get_discovery_time(cfg, city, event)
        assert hours <= 2.0 * workshop.detection_time_modifier * cfg.settings.discovery_speed_multiplier


class TestMetricBoundsFromConfig:
    def test_every_global_metric_takes_bounds_from_metrics_yaml(self):
        cfg, city = build_city(CONFIG_DIR)
        for name, spec in cfg.metrics_global_raw.items():
            metric = city.get_metric(name)
            assert metric is not None
            assert metric.min_value == float(spec["min"])
            assert metric.max_value == float(spec["max"])
