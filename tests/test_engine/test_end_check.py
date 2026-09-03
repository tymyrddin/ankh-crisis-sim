from __future__ import annotations

from dataclasses import replace
from pathlib import Path

from src.config.loader import build_city
from src.engine.end_check import check_end_conditions

CONFIG_DIR = Path(__file__).parent.parent.parent / "config"


class TestMetricBelow:
    def test_revolt_fires_when_legitimacy_below_threshold(self):
        cfg, city = build_city(CONFIG_DIR)
        city.legitimacy.set(5.0, tick=0, cause="test setup")

        result = check_end_conditions(cfg, city, elapsed_days=10)

        assert result is not None
        assert result.condition_id == "revolt"

    def test_revolt_not_triggered_above_threshold(self):
        cfg, city = build_city(CONFIG_DIR)
        city.public_trust.set(60.0, tick=0, cause="test setup")
        city.legitimacy.set(50.0, tick=0, cause="test setup")
        city.budget.apply(1000, tick=0, cause="test setup")
        city.political_stability.set(60.0, tick=0, cause="test setup")

        result = check_end_conditions(cfg, city, elapsed_days=10)

        # not a loss condition, if anything fired
        assert result is None or result.condition_id not in (
            "revolt", "assassination", "election_loss", "bankruptcy"
        )

    def test_assassination_fires_below_stability_threshold(self):
        cfg, city = build_city(CONFIG_DIR)
        city.political_stability.set(3.0, tick=0, cause="test setup")

        result = check_end_conditions(cfg, city, elapsed_days=10)

        assert result is not None
        # election_loss might fire first if trust is also low, but assassination has lower threshold
        assert result.condition_id in ("assassination", "election_loss")


class TestSustainedDays:
    def test_election_loss_requires_sustained_trust_collapse(self):
        cfg, city = build_city(CONFIG_DIR)
        city.public_trust.set(10.0, tick=0, cause="test setup")

        result = check_end_conditions(cfg, city, elapsed_days=5)

        assert result is None or result.condition_id != "election_loss"

    def test_election_loss_fires_after_sustained_window(self):
        cfg, city = build_city(CONFIG_DIR)
        # 31 days of hourly snapshots below the threshold
        for tick in range(31 * 24 + 5):
            city.public_trust.set(10.0, tick=tick, cause="prolonged collapse")

        result = check_end_conditions(cfg, city, elapsed_days=31)

        assert result is not None
        assert result.condition_id == "election_loss"


    def test_sustained_window_counts_ticks_not_snapshots(self):
        cfg, city = build_city(CONFIG_DIR)
        city.budget.set(500.0, tick=0, cause="test setup")
        city.budget.set(-100.0, tick=24 * 2, cause="overspend on day 2")

        too_soon = check_end_conditions(cfg, city, elapsed_days=10)
        assert too_soon is None or too_soon.condition_id != "bankruptcy"

        result = check_end_conditions(cfg, city, elapsed_days=16)
        assert result is not None
        assert result.condition_id == "bankruptcy"


class TestDistrictsInCrisis:
    def test_complete_failure_fires_with_enough_crisis_districts(self):
        cfg, city = build_city(CONFIG_DIR)
        crisis_districts = list(city.districts.values())[:5]
        for d in crisis_districts:
            buildings = list(d.buildings.values())
            for b in buildings[: len(buildings) // 2 + 1]:
                b.fail(tick=1, event_id=f"forced_{d.id}")

        result = check_end_conditions(cfg, city, elapsed_days=10)

        assert result is not None
        assert result.condition_id == "complete_failure"


class TestTermCompletion:
    def test_term_completion_fires_at_yaml_days(self):
        cfg, city = build_city(CONFIG_DIR)
        city.public_trust.set(60.0, tick=0, cause="test setup")
        city.legitimacy.set(50.0, tick=0, cause="test setup")
        city.political_stability.set(60.0, tick=0, cause="test setup")

        result = check_end_conditions(cfg, city, elapsed_days=1460)

        assert result is not None
        assert result.condition_id == "term_completion"


class TestGameDurationDaysOverride:
    def test_override_below_yaml_default_ends_game_sooner(self):
        cfg, city = build_city(CONFIG_DIR)
        city.public_trust.set(60.0, tick=0, cause="test setup")
        city.legitimacy.set(50.0, tick=0, cause="test setup")
        city.political_stability.set(60.0, tick=0, cause="test setup")

        cfg.settings = replace(cfg.settings, game_duration_days=100)

        early = check_end_conditions(cfg, city, elapsed_days=50)
        assert early is None or early.condition_id != "term_completion"

        result = check_end_conditions(cfg, city, elapsed_days=100)
        assert result is not None
        assert result.condition_id == "term_completion"

    def test_zero_override_falls_back_to_yaml(self):
        cfg, city = build_city(CONFIG_DIR)
        city.public_trust.set(60.0, tick=0, cause="test setup")
        city.legitimacy.set(50.0, tick=0, cause="test setup")
        city.political_stability.set(60.0, tick=0, cause="test setup")

        cfg.settings = replace(cfg.settings, game_duration_days=0)

        early = check_end_conditions(cfg, city, elapsed_days=1459)
        assert early is None or early.condition_id != "term_completion"

        result = check_end_conditions(cfg, city, elapsed_days=1460)
        assert result is not None
        assert result.condition_id == "term_completion"


class TestPlayerActionTriggers:
    def test_resignation_and_retirement_not_triggered_by_check_loop(self):
        cfg, city = build_city(CONFIG_DIR)
        city.public_trust.set(60.0, tick=0, cause="test setup")
        city.legitimacy.set(50.0, tick=0, cause="test setup")
        city.political_stability.set(60.0, tick=0, cause="test setup")

        result = check_end_conditions(cfg, city, elapsed_days=500)

        assert result is None or result.condition_id not in ("resignation", "early_retirement")
