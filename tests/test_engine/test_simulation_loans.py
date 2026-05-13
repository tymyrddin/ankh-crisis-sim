"""Tests for Simulation.emergency_borrow: lender lookup, budget credit, and political costs.

Covers the path in src/engine/simulation.py:159-194 which was uncovered before this file.
"""

from __future__ import annotations

from pathlib import Path

from src.engine.simulation import Simulation

CONFIG_DIR = Path(__file__).parent.parent.parent / "config"


def _fresh_sim() -> Simulation:
    sim = Simulation(config_dir=CONFIG_DIR)
    sim.initialise()
    return sim


class TestEmergencyBorrowHappyPath:
    def test_royal_bank_credits_budget_and_raises_regulatory_pressure(self):
        sim = _fresh_sim()
        budget_before = sim.city.budget.value
        reg_before = sim.city.regulatory_pressure.value
        stability_before = sim.city.political_stability.value

        result = sim.emergency_borrow("royal_bank")

        assert result.success
        assert sim.city.budget.value == budget_before + 2000
        assert sim.city.regulatory_pressure.value == reg_before + 15
        # Royal bank has no stability_cost, so stability stays put
        assert sim.city.political_stability.value == stability_before
        assert result.cost == -2000
        assert "Royal Bank" in result.message

    def test_ueberwald_credits_budget_and_drops_stability(self):
        sim = _fresh_sim()
        budget_before = sim.city.budget.value
        reg_before = sim.city.regulatory_pressure.value
        stability_before = sim.city.political_stability.value

        result = sim.emergency_borrow("ueberwald")

        assert result.success
        assert sim.city.budget.value == budget_before + 3000
        # Überwald has no regulatory_pressure_cost
        assert sim.city.regulatory_pressure.value == reg_before
        assert sim.city.political_stability.value == stability_before - 8
        assert result.cost == -3000


class TestEmergencyBorrowErrors:
    def test_unknown_lender_returns_failure(self):
        sim = _fresh_sim()
        budget_before = sim.city.budget.value

        result = sim.emergency_borrow("nonexistent_lender")

        assert not result.success
        assert "Unknown lender" in result.message
        assert sim.city.budget.value == budget_before

    def test_unavailable_lender_returns_failure(self):
        sim = _fresh_sim()
        # Force the royal_bank entry to unavailable
        sim.cfg.budget_raw["emergency_borrowing"]["royal_bank"]["available"] = False
        budget_before = sim.city.budget.value

        result = sim.emergency_borrow("royal_bank")

        assert not result.success
        assert "not currently available" in result.message
        assert sim.city.budget.value == budget_before


class TestEmergencyBorrowRepeated:
    def test_repeated_borrow_accumulates_budget_and_costs(self):
        sim = _fresh_sim()
        budget_before = sim.city.budget.value
        reg_before = sim.city.regulatory_pressure.value

        sim.emergency_borrow("royal_bank")
        sim.emergency_borrow("royal_bank")

        assert sim.city.budget.value == budget_before + 4000
        assert sim.city.regulatory_pressure.value == reg_before + 30
