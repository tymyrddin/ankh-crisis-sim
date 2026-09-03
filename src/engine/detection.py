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
    district = city.districts.get(event.target_district_id)
    if not district:
        return 1.0

    template = cfg.template(event.template_id)
    low, high = template.discovery_hours if template and template.discovery_hours else district.discovery_time_hours
    if low == 0 and high == 0:
        return 0.0

    base_hours = random.uniform(low, high)

    building = district.buildings.get(event.target_building_id)
    if building:
        base_hours *= building.detection_time_modifier

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
