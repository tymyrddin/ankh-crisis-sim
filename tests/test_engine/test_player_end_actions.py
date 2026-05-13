"""Tests for Simulation.resign() and Simulation.retire()."""

from __future__ import annotations

from pathlib import Path

from src.engine.simulation import Simulation

CONFIG_DIR = Path(__file__).parent.parent.parent / "config"


def _fresh_sim() -> Simulation:
    sim = Simulation(config_dir=CONFIG_DIR)
    sim.initialise()
    return sim


class TestResign:
    def test_resign_returns_resignation_end_result(self):
        sim = _fresh_sim()

        result = sim.resign()

        assert result.triggered
        assert result.condition_id == "resignation"
        assert "step down" in result.narrative.lower() or len(result.narrative) > 0


class TestRetire:
    def test_retire_before_min_days_blocks_with_message(self):
        sim = _fresh_sim()
        # clock.elapsed_days is 0 at fresh init; min_days for early_retirement is 365
        result = sim.retire()

        assert not result.triggered
        assert result.condition_id == "early_retirement"
        assert "365" in result.narrative or "requires" in result.narrative.lower()

    def test_retire_after_min_days_triggers(self):
        sim = _fresh_sim()
        # Advance the clock past min_days (365 * 24 ticks)
        sim.clock.tick = 365 * 24 + 1

        result = sim.retire()

        assert result.triggered
        assert result.condition_id == "early_retirement"
