"""Detection system — determines when hidden failures become visible."""

from __future__ import annotations

import random

from src.config.loader import GameConfig
from src.models.building import Building
from src.models.city import City
from src.models.event import GameEvent


def _get_discovery_time(
    cfg: GameConfig,
    city: City,
    event: GameEvent,
) -> float:
    """Calculate how many ticks (hours) until this event is discovered."""
    district = city.districts.get(event.target_district_id)
    if not district:
        return 1.0

    # Base discovery time from district
    low, high = district.discovery_time_hours
    if low == 0 and high == 0:
        return 0.0  # immediate (e.g., river fires)

    base_hours = random.uniform(low, high)

    # Modify by building type
    building = district.buildings.get(event.target_building_id)
    if building:
        bt_modifiers = cfg.detection_raw.get("building_type_modifiers", {})
        modifier = bt_modifiers.get(building.type_id, 1.0)

        # Override for specific buildings (e.g., cockbill pride)
        if building.detection_time_modifier_override is not None:
            modifier = building.detection_time_modifier_override

        base_hours *= modifier

    # Check for incident-type overrides
    incident_discovery = cfg.detection_raw.get("incident_type_discovery", {})
    for incident_type, idata in incident_discovery.items():
        # Simple heuristic: if the event domain matches an incident type keyword
        if event.domain and event.domain in incident_type:
            hours = idata.get("hours", base_hours)
            if isinstance(hours, list):
                base_hours = min(base_hours, random.uniform(hours[0], hours[1]))
            elif isinstance(hours, (int, float)):
                base_hours = min(base_hours, hours)

    return max(0.0, base_hours)


def process_detection(
    cfg: GameConfig,
    city: City,
    tick: int,
) -> list[GameEvent]:
    """Check all hidden events and detect those whose discovery time has elapsed."""
    newly_detected = []

    for event in city.events:
        if not event.is_active:
            continue
        if event.is_visible:
            continue  # already detected

        hours_elapsed = tick - event.created_tick
        discovery_time = _get_discovery_time(cfg, city, event)

        if hours_elapsed >= discovery_time:
            event.detect(tick)

            # Mark the building as no longer hidden
            building = city.get_building(event.target_building_id)
            if building:
                building.hidden_failure = False

            newly_detected.append(event)

    return newly_detected