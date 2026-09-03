from __future__ import annotations

import random

from src.config.loader import GameConfig
from src.models.city import City
from src.models.event import GameEvent


def generate_headline(
    cfg: GameConfig,
    city: City,
    event: GameEvent,
) -> str:
    if event.headline:
        return event.headline

    # residential pool first, then domain, then general
    pools = []
    if event.residential_impact:
        pools.extend(cfg.headlines_raw.get("residential", []))
    domain = event.domain or "general"
    pools.extend(cfg.headlines_raw.get(domain, []))
    pools.extend(cfg.headlines_raw.get("general", []))
    if not pools:
        return event.name

    template = random.choice(pools)

    district = city.districts.get(event.target_district_id)
    building = city.get_building(event.target_building_id)

    return template.format(
        district=district.name if district else "unknown",
        building=building.name if building else "unknown",
        duration=_format_duration(event, city),
        affected_count=_count_affected(event, city),
    )


def generate_story(
    cfg: GameConfig,
    city: City,
    event: GameEvent,
    tick: int,
) -> str:
    template_cfg = cfg.template(event.template_id)
    story_entries = template_cfg.stories if template_cfg and template_cfg.stories else None
    if not story_entries:
        story_entries = cfg.stories_raw.get(event.domain or "general", [])
    if not story_entries:
        return ""

    entry = random.choice(story_entries)
    template = entry if isinstance(entry, str) else entry.get("story", "")

    district = city.districts.get(event.target_district_id)
    building = city.get_building(event.target_building_id)

    detection_narrative = _get_detection_narrative(cfg, event, tick)
    political_narrative = _get_political_narrative(cfg, city)
    stressor_narrative = _get_stressor_narrative(city)

    try:
        return template.format(
            district=district.name if district else "unknown",
            building=building.name if building else "unknown",
            duration=_format_duration(event, city),
            affected_count=_count_affected(event, city),
            detection_narrative=detection_narrative,
            political_narrative=political_narrative,
            stressor_narrative=stressor_narrative,
            remedy=event.remedy_applied or "none",
        )
    except (KeyError, IndexError):
        return template  # a placeholder the story does not know


def _format_duration(event: GameEvent, city: City) -> str:
    if event.detected_tick is None:
        return "an unknown time"
    hours = max(0, event.detected_tick - event.created_tick)

    if hours < 24:
        return f"{hours} hours"
    days = hours // 24
    return f"{days} day{'s' if days != 1 else ''}"


def _count_affected(event: GameEvent, city: City) -> int:
    district = city.districts.get(event.target_district_id)
    if not district:
        return 0
    return district.failed_building_count + district.degraded_building_count


def _get_detection_narrative(cfg: GameConfig, event: GameEvent, tick: int) -> str:
    narratives = cfg.stories_raw.get("detection_narratives", {})
    if event.created_tick == event.detected_tick:
        return narratives.get("immediate", "The failure was noticed immediately.")

    delay = (event.detected_tick or tick) - event.created_tick
    if delay > 120:
        template = narratives.get("pride_concealment", narratives.get("never_reported", ""))
    elif delay > 48:
        template = narratives.get("delayed_cascade", "")
    else:
        template = narratives.get("delayed_citizen", "")

    try:
        return template.format(delay=delay)
    except (KeyError, IndexError):
        return template


def _get_political_narrative(cfg: GameConfig, city: City) -> str:
    narratives = cfg.stories_raw.get("political_narratives", {})
    pressure = city.regulatory_pressure.value

    if pressure > 60:
        return narratives.get("guilds_demand", "The guilds have demanded action.").format(guild="Merchants")
    elif pressure > 40:
        return narratives.get("media_pressure", "The press is asking questions.")
    else:
        return narratives.get("silence", "The Palace has said nothing.")


def _get_stressor_narrative(city: City) -> str:
    if not city.stressors:
        return "underlying conditions"

    worst = max(city.stressors, key=lambda k: city.stressors[k] if isinstance(city.stressors[k], (int, float)) else 0)
    labels = {
        "underinvestment": "years of underinvestment",
        "just_in_time": "fragile supply chains",
        "vendor_monoculture": "dependence on a single provider",
        "social_inequality": "deep social inequality",
        "organisational_fragmentation": "nobody being in charge",
    }
    return labels.get(worst, "underlying conditions")
