from __future__ import annotations

import random
from pathlib import Path

from src.config.loader import EventTemplate, build_city
from src.engine.events import generate_events

CONFIG_DIR = Path(__file__).parent.parent.parent / "config"


def _one_template_city():
    cfg, city = build_city(CONFIG_DIR)
    cfg.settings.event_rate_multiplier = 1.0
    cfg.event_templates = [EventTemplate(
        id="t", name="t", category="c", domain="water",
        target_districts=["isle_of_gods"],  # failure multiplier 1.0
        probability_base=0.24,  # per day, so 0.01 per tick
    )]
    return cfg, city


def test_probability_base_is_per_day(monkeypatch):
    cfg, city = _one_template_city()
    monkeypatch.setattr(random, "random", lambda: 0.0099)
    assert len(generate_events(cfg, city, tick=1)) == 1

    cfg, city = _one_template_city()
    monkeypatch.setattr(random, "random", lambda: 0.0101)
    assert generate_events(cfg, city, tick=1) == []
