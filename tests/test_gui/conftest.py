from __future__ import annotations

import os
from pathlib import Path

import pytest

CONFIG_DIR = Path(__file__).parent.parent.parent / "config"


def _display_available() -> bool:
    if not os.environ.get("DISPLAY") and os.name != "nt":
        return False
    try:
        import tkinter as tk
        root = tk.Tk()
        root.withdraw()
        root.destroy()
        return True
    except Exception:
        return False


_HAS_DISPLAY = _display_available()


@pytest.fixture
def ctk_root():
    if not _HAS_DISPLAY:
        pytest.skip("No display available for GUI smoke test")
    import customtkinter as ctk
    root = ctk.CTk()
    root.withdraw()
    yield root
    try:
        root.destroy()
    except Exception:
        pass


@pytest.fixture
def loaded_city():
    from src.config.loader import build_city
    cfg, city = build_city(CONFIG_DIR)
    return cfg, city


@pytest.fixture
def detected_event_water(loaded_city):
    cfg, city = loaded_city
    district = city.districts["the_shades"]
    building = next(iter(district.buildings.values()))
    building.fail(tick=1, event_id="smoke_evt_water")
    from src.models.event import EventPhase, GameEvent
    event = GameEvent(
        id="smoke_evt_water",
        template_id="pump_failure",
        name="Smoke Water Failure",
        category="degradation_and_neglect",
        domain="water",
        phase=EventPhase.DETECTED,
        target_district_id=district.id,
        target_building_id=building.id,
        created_tick=1,
        detected_tick=2,
    )
    city.events.append(event)
    return event, district, building


@pytest.fixture
def detected_event_communications(loaded_city):
    cfg, city = loaded_city
    target_district = None
    target_building = None
    for d in city.districts.values():
        for b in d.buildings.values():
            if b.type_id == "clacks_tower":
                target_district = d
                target_building = b
                break
        if target_district:
            break
    if not target_district or not target_building:
        pytest.skip("No clacks_tower building found in config")
    target_building.fail(tick=1, event_id="smoke_evt_comms")
    from src.models.event import EventPhase, GameEvent
    event = GameEvent(
        id="smoke_evt_comms",
        template_id="clacks_degradation",
        name="Smoke Comms Failure",
        category="degradation_and_neglect",
        domain="communications",
        phase=EventPhase.DETECTED,
        target_district_id=target_district.id,
        target_building_id=target_building.id,
        created_tick=1,
        detected_tick=2,
    )
    city.events.append(event)
    return event, target_district, target_building
