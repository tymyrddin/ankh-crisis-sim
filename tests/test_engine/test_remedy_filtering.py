from __future__ import annotations

from pathlib import Path

from src.config.loader import build_city
from src.engine.remedies import get_available_remedies
from src.models.event import EventPhase, GameEvent

CONFIG_DIR = Path(__file__).parent.parent.parent / "config"

UNIVERSAL = {"press_statement", "operational_workaround", "do_nothing"}


def _evt(domain: str) -> GameEvent:
    return GameEvent(
        id="x", template_id="x", name="x", category="x",
        domain=domain, phase=EventPhase.DETECTED,
    )


class TestFiltering:
    def test_communications_offers_only_two_pathways_plus_universals(self):
        cfg, _ = build_city(CONFIG_DIR)
        ids = {r.id for r in get_available_remedies(cfg, _evt("communications"))}

        assert ids == UNIVERSAL | {"technical_restoration", "resilience_investment"}

    def test_transport_offers_only_two_pathways_plus_universals(self):
        cfg, _ = build_city(CONFIG_DIR)
        ids = {r.id for r in get_available_remedies(cfg, _evt("transport"))}

        assert ids == UNIVERSAL | {"technical_restoration", "resilience_investment"}

    def test_water_offers_all_four_pathways(self):
        cfg, _ = build_city(CONFIG_DIR)
        ids = {r.id for r in get_available_remedies(cfg, _evt("water"))}

        expected = UNIVERSAL | {
            "technical_restoration",
            "resilience_investment",
            "public_compensation",
            "accountability_actions",
        }
        assert ids == expected

    def test_commercial_excludes_accountability(self):
        cfg, _ = build_city(CONFIG_DIR)
        ids = {r.id for r in get_available_remedies(cfg, _evt("commercial"))}

        expected = UNIVERSAL | {
            "technical_restoration",
            "resilience_investment",
            "public_compensation",
        }
        assert ids == expected
        assert "accountability_actions" not in ids

    def test_no_event_returns_all_remedies(self):
        cfg, _ = build_city(CONFIG_DIR)
        ids = {r.id for r in get_available_remedies(cfg)}

        assert ids == UNIVERSAL | {
            "technical_restoration",
            "resilience_investment",
            "public_compensation",
            "accountability_actions",
        }

    def test_universals_never_filtered_out(self):
        cfg, _ = build_city(CONFIG_DIR)
        for domain in ["energy", "water", "communications", "transport",
                       "public_services", "commercial", "residential"]:
            ids = {r.id for r in get_available_remedies(cfg, _evt(domain))}
            assert UNIVERSAL.issubset(ids), f"Universals missing for domain {domain}: {ids}"


class TestResidentialIntersect:
    def test_residential_water_event_excludes_accountability(self):
        cfg, _ = build_city(CONFIG_DIR)
        event = GameEvent(
            id="x", template_id="x", name="x", category="x",
            domain="water", phase=EventPhase.DETECTED,
            residential_impact=True,
        )
        ids = {r.id for r in get_available_remedies(cfg, event)}

        expected = UNIVERSAL | {
            "technical_restoration",
            "resilience_investment",
            "public_compensation",
        }
        assert ids == expected
        assert "accountability_actions" not in ids

    def test_non_residential_water_still_offers_accountability(self):
        cfg, _ = build_city(CONFIG_DIR)
        event = GameEvent(
            id="x", template_id="x", name="x", category="x",
            domain="water", phase=EventPhase.DETECTED,
            residential_impact=False,
        )
        ids = {r.id for r in get_available_remedies(cfg, event)}

        assert "accountability_actions" in ids
