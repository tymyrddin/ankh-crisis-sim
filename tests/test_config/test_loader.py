"""Tests for config loading and city assembly."""

from pathlib import Path

from src.config.loader import build_city, load_config

CONFIG_DIR = Path(__file__).parent.parent.parent / "config"


class TestLoadConfig:
    def test_loads_without_error(self):
        cfg = load_config(CONFIG_DIR)
        assert cfg is not None

    def test_has_time_settings(self):
        cfg = load_config(CONFIG_DIR)
        assert cfg.time.tick_hours == 1
        assert cfg.time.ticks_per_day == 24
        assert cfg.time.term_length_days == 1460

    def test_has_active_districts(self):
        cfg = load_config(CONFIG_DIR)
        assert len(cfg.active_districts) == 8
        assert "nap_hill" in cfg.active_districts
        assert "the_shades" in cfg.active_districts

    def test_has_remedies(self):
        cfg = load_config(CONFIG_DIR)
        assert len(cfg.remedies) >= 7
        assert "technical_restoration" in cfg.remedies
        assert "do_nothing" in cfg.remedies

    def test_has_event_templates(self):
        cfg = load_config(CONFIG_DIR)
        assert len(cfg.event_templates) > 0
        ids = [e.id for e in cfg.event_templates]
        assert "pump_failure" in ids

    def test_has_stressors(self):
        cfg = load_config(CONFIG_DIR)
        assert "underinvestment" in cfg.stressors
        assert cfg.stressors["underinvestment"].starting_level == 0.6

    def test_has_building_types(self):
        cfg = load_config(CONFIG_DIR)
        assert "guild_hq" in cfg.building_types
        assert "tavern" in cfg.building_types
        assert "palace" in cfg.building_types

    def test_has_end_conditions(self):
        cfg = load_config(CONFIG_DIR)
        assert len(cfg.end_conditions) > 0
        ids = [e.id for e in cfg.end_conditions]
        assert "election_loss" in ids
        assert "bankruptcy" in ids


class TestBuildCity:
    def test_builds_without_error(self):
        cfg, city = build_city(CONFIG_DIR)
        assert city is not None
        assert cfg is not None

    def test_has_all_districts(self):
        _, city = build_city(CONFIG_DIR)
        assert len(city.districts) == 8
        assert "nap_hill" in city.districts
        assert "the_shades" in city.districts
        assert "river_ankh" in city.districts

    def test_district_properties(self):
        _, city = build_city(CONFIG_DIR)
        nap = city.districts["nap_hill"]
        assert nap.wealth == 90
        assert nap.political_influence == 2.0
        assert nap.local_trust.value == 75

        shades = city.districts["the_shades"]
        assert shades.wealth == 12
        assert shades.local_trust.value == 15

    def test_buildings_attached_to_districts(self):
        _, city = build_city(CONFIG_DIR)
        # Mended Drum should be in Merchant Quarter
        mq = city.districts["merchant_quarter"]
        assert "mended_drum" in mq.buildings
        assert mq.buildings["mended_drum"].name == "The Mended Drum"

    def test_global_metrics_from_config(self):
        _, city = build_city(CONFIG_DIR)
        assert city.public_trust.value == 68
        assert city.budget.value == 15000
        assert city.regulatory_pressure.value == 18
        assert city.political_stability.value == 75
        assert city.legitimacy.value == 82

    def test_stressor_levels_initialised(self):
        _, city = build_city(CONFIG_DIR)
        assert city.stressors["underinvestment"] == 0.6
        assert city.stressors["just_in_time"] == 0.7

    def test_building_dependencies_merged_from_type(self):
        cfg, city = build_city(CONFIG_DIR)
        # Assassins' Guild should have guild_hq dependencies
        ag = city.districts["merchant_quarter"].buildings.get("assassins_guild")
        assert ag is not None
        assert "communications" in ag.dependencies.critical