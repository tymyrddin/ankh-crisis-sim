from __future__ import annotations

import random

from src.config.loader import GameConfig
from src.models.city import City
from src.models.event import GameEvent


def _get_discovery_time(
    cfg: GameConfig,
    city: City,
    event: GameEvent,
) -> float:
    """Hours until the event surfaces."""
    district = city.districts.get(event.target_district_id)
    if not district:
        return 1.0

    low, high = district.discovery_time_hours
    if low == 0 and high == 0:
        return 0.0

    base_hours = random.uniform(low, high)

    building = district.buildings.get(event.target_building_id)
    if building:
        bt_modifiers = cfg.detection_raw.get("building_type_modifiers", {})
        modifier = bt_modifiers.get(building.type_id, 1.0)

        # per-building override (Cockbill pride)
        if building.detection_time_modifier_override is not None:
            modifier = building.detection_time_modifier_override

        base_hours *= modifier

    incident_discovery = cfg.detection_raw.get("incident_type_discovery", {})
    for incident_type, idata in incident_discovery.items():
        # substring match on the incident key
        if event.domain and event.domain in incident_type:
            hours = idata.get("hours", base_hours)
            if isinstance(hours, list):
                base_hours = min(base_hours, random.uniform(hours[0], hours[1]))
            elif isinstance(hours, (int, float)):
                base_hours = min(base_hours, hours)

    base_hours *= cfg.settings.discovery_speed_multiplier
    return max(0.0, base_hours)


def process_detection(
    cfg: GameConfig,
    city: City,
    tick: int,
) -> list[GameEvent]:
    newly_detected = []

    for event in city.events:
        if not event.is_active:
            continue
        if event.is_visible:
            continue

        # rolled once, then cached
        if event.discovery_time_hours is None:
            event.discovery_time_hours = _get_discovery_time(cfg, city, event)

        hours_elapsed = tick - event.created_tick
        if hours_elapsed >= event.discovery_time_hours:
            event.detect(tick)

            building = city.get_building(event.target_building_id)
            if building:
                building.hidden_failure = False

            newly_detected.append(event)

    return newly_detected