from __future__ import annotations

from pathlib import Path

from src.config.loader import build_city
from src.engine.narrative import generate_headline
from src.models.event import EventPhase, GameEvent

CONFIG_DIR = Path(__file__).parent.parent.parent / "config"


class TestResidentialTemplates:
    def test_residential_event_templates_present(self):
        cfg, _ = build_city(CONFIG_DIR)
        residential_ids = {
            t.id for t in cfg.event_templates if t.residential_impact
        }
        assert "tenement_subsidence" in residential_ids
        assert "heating_failure_cold_spell" in residential_ids
        assert "civic_amenity_neglect" in residential_ids

    def test_residential_templates_target_residential_buildings(self):
        cfg, _ = build_city(CONFIG_DIR)
        for t in cfg.event_templates:
            if not t.residential_impact:
                continue
            residential_types = {"slum_dwelling", "middle_class_housing", "civic_amenity"}
            assert any(bt in residential_types for bt in t.target_building_types), (
                f"{t.id} flagged residential_impact but targets {t.target_building_types}"
            )

    def test_residential_templates_keep_utility_domain(self):
        cfg, _ = build_city(CONFIG_DIR)
        for t in cfg.event_templates:
            if not t.residential_impact:
                continue
            assert t.domain in {"water", "energy", "communications", "transport",
                                "public_services", "commercial"}, (
                f"{t.id} has out-of-bounds domain {t.domain!r}"
            )


class TestHeadlinePool:
    def test_residential_impact_event_can_pull_residential_headline(self):
        cfg, city = build_city(CONFIG_DIR)
        district = city.districts["the_shades"]
        building = next(iter(district.buildings.values()))

        event = GameEvent(
            id="x", template_id="x", name="x", category="x",
            domain="water", phase=EventPhase.DETECTED,
            target_district_id=district.id,
            target_building_id=building.id,
            residential_impact=True,
        )

        results = set()
        for _ in range(50):
            results.add(generate_headline(cfg, city, event))
        assert all(isinstance(r, str) and r for r in results)

    def test_residential_pool_never_picked_without_flag(self):
        cfg, city = build_city(CONFIG_DIR)
        residential_templates = set(cfg.headlines_raw.get("residential", []))
        assert residential_templates

        district = city.districts["the_shades"]
        building = next(iter(district.buildings.values()))
        event = GameEvent(
            id="x", template_id="x", name="x", category="x",
            domain="water", phase=EventPhase.DETECTED,
            target_district_id=district.id,
            target_building_id=building.id,
            residential_impact=False,
        )

        for _ in range(50):
            h = generate_headline(cfg, city, event)
            # the templates contain {district}; format the same way
            substituted_residential = {
                t.format(district=district.name, building=building.name, duration="", affected_count=0)
                for t in residential_templates
            }
            assert h not in substituted_residential
