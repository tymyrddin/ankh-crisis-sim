"""Event generation: rolls against probabilities weighted by stressors and neglect."""

from __future__ import annotations

import random
import uuid

from src.config.loader import EventTemplate, GameConfig
from src.models.building import Building
from src.models.city import City
from src.models.event import DelayedEffect, EventPhase, GameEvent, MetricEffect


# District stressor labels → local probability multiplier
# e.g. just_in_time: amplifier raises event probability for transport/commercial events
_DISTRICT_STRESSOR_LABEL_MODS: dict[str, float] = {
    "amplifier": 1.5,
    "extreme":   2.0,
    "chronic":   1.5,
    "high":      1.3,
    "moderate":  1.1,
    "victim":    1.2,
    "beneficiary": 0.8,
}


def _calculate_probability(
    template: EventTemplate,
    city: City,
    district_failure_mod: float,
    district_stressors: dict | None = None,
) -> float:
    """Calculate adjusted event probability based on stressors and district quality."""
    prob = template.probability_base * district_failure_mod

    for stressor_id, multiplier in template.stressor_amplifiers.items():
        level = city.stressors.get(stressor_id, 0.0)
        if isinstance(level, (int, float)):
            prob *= 1.0 + (level * (multiplier - 1.0))

        # District-local stressor label: further amplifies events in sensitive districts
        if district_stressors:
            label = district_stressors.get(stressor_id)
            if isinstance(label, str):
                prob *= _DISTRICT_STRESSOR_LABEL_MODS.get(label, 1.0)

    return min(prob, 0.5)  # cap at 50% per tick


def _find_target_building(
    template: EventTemplate,
    city: City,
    district_id: str,
) -> Building | None:
    """Find a valid target building in the district for this event."""
    district = city.districts.get(district_id)
    if not district:
        return None

    candidates = []
    for building in district.buildings.values():
        if building.active_event_id:
            continue  # already has an active event
        if template.target_buildings and building.id not in template.target_buildings:
            continue
        if template.target_building_types and building.type_id not in template.target_building_types:
            continue
        candidates.append(building)

    if not candidates:
        return None
    # Buildings with high recurrence_risk are more likely to be targeted again
    weights = [1.0 + building.recurrence_risk * 9.0 for building in candidates]
    return random.choices(candidates, weights=weights, k=1)[0]


def _just_in_time_buffer_reduction(cfg: GameConfig, city: City) -> int:
    """Hours to subtract from delayed-effect timing under high just_in_time pressure.

    `just_in_time.shortens_buffer_days` declares how many days of buffer evaporate
    at full stressor level. Linearly scaled by the current stressor value.
    """
    sc = cfg.stressors.get("just_in_time")
    if not sc:
        return 0
    level = city.stressors.get("just_in_time", 0.0)
    if level <= 0:
        return 0
    days = 0
    for eff in sc.raw.get("effects", []):
        if "shortens_buffer_days" in eff:
            days = int(eff["shortens_buffer_days"])
            break
    return int(days * 24 * level)


def _vendor_monoculture_duplicates(cfg: GameConfig, city: City, template: EventTemplate) -> bool:
    """Should this event template duplicate to a second district?

    `vendor_monoculture.multi_district_impact` flags that supply_chain_failure
    events under a monoculture vendor can hit multiple districts simultaneously.
    Probability scales with the stressor level.
    """
    if template.category != "supply_chain_failure":
        return False
    sc = cfg.stressors.get("vendor_monoculture")
    if not sc:
        return False
    if not any("multi_district_impact" in eff for eff in sc.raw.get("effects", [])):
        return False
    level = city.stressors.get("vendor_monoculture", 0.0)
    return random.random() < level * 0.5  # max 50% chance at full stressor


def generate_events(
    cfg: GameConfig,
    city: City,
    tick: int,
) -> list[GameEvent]:
    """Roll for each event template against each eligible district. Returns new events."""
    new_events = []

    buffer_reduction_hours = _just_in_time_buffer_reduction(cfg, city)

    for template in cfg.event_templates:
        # Determine eligible districts
        if template.target_districts:
            eligible = [d for d in template.target_districts if d in city.districts]
        else:
            eligible = list(city.districts.keys())

        for district_id in eligible:
            district = city.districts[district_id]
            prob = _calculate_probability(
                template, city, district.failure_probability_modifier, district.stressors
            )
            prob *= cfg.settings.event_rate_multiplier

            if random.random() >= prob:
                continue

            # Find a target building
            building = _find_target_building(template, city, district_id)
            if not building:
                continue

            # Create the event
            event_id = f"{template.id}_{uuid.uuid4().hex[:8]}"

            # Copy immediate effects, adjusting district scope
            immediate = []
            for eff in template.immediate_effects:
                immediate.append(MetricEffect(
                    metric=eff.metric,
                    delta=eff.delta,
                    scope=eff.scope,
                    district_id=district_id if eff.scope == "district" else eff.district_id,
                ))

            # Copy delayed effects; just_in_time shortens the buffer days.
            delayed = []
            for de in template.delayed_effects:
                adjusted_delay = max(0, de.delay_hours - buffer_reduction_hours)
                delayed.append(DelayedEffect(
                    delay_hours=adjusted_delay,
                    effects=[MetricEffect(
                        metric=e.metric,
                        delta=e.delta,
                        scope=e.scope,
                        district_id=e.district_id,
                    ) for e in de.effects],
                ))

            # Generate headline
            headline = ""
            if template.headlines:
                headline = random.choice(template.headlines).format(
                    district=district.name,
                    building=building.name,
                )

            event = GameEvent(
                id=event_id,
                template_id=template.id,
                name=template.name,
                category=template.category,
                domain=template.domain,
                phase=EventPhase.HIDDEN,
                target_district_id=district_id,
                target_building_id=building.id,
                created_tick=tick,
                immediate_effects=immediate,
                delayed_effects=delayed,
                duration_penalty_per_day=template.duration_penalty_per_day,
                duration_penalty_metric=template.duration_penalty_metric,
                cascade_dependency=template.cascade_dependency,
                cascade_scope=template.cascade_scope,
                headline=headline,
                residential_impact=template.residential_impact,
            )

            # Apply the failure to the building
            building.fail(tick, event_id)
            building.hidden_failure = True

            new_events.append(event)

            # vendor_monoculture multi-district impact: supply-chain failures
            # under a monoculture vendor can spread to a second district.
            if _vendor_monoculture_duplicates(cfg, city, template):
                other_district_ids = [
                    d for d in eligible
                    if d != district_id and city.districts[d].buildings
                ]
                if other_district_ids:
                    other_id = random.choice(other_district_ids)
                    other_building = _find_target_building(template, city, other_id)
                    if other_building:
                        dup_id = f"{template.id}_{uuid.uuid4().hex[:8]}"
                        dup_event = GameEvent(
                            id=dup_id,
                            template_id=template.id,
                            name=f"{template.name} (vendor knock-on)",
                            category=template.category,
                            domain=template.domain,
                            phase=EventPhase.HIDDEN,
                            target_district_id=other_id,
                            target_building_id=other_building.id,
                            created_tick=tick,
                            immediate_effects=[
                                MetricEffect(
                                    metric=e.metric, delta=e.delta, scope=e.scope,
                                    district_id=other_id if e.scope == "district" else e.district_id,
                                ) for e in template.immediate_effects
                            ],
                            delayed_effects=[
                                DelayedEffect(
                                    delay_hours=max(0, de.delay_hours - buffer_reduction_hours),
                                    effects=[MetricEffect(
                                        metric=e.metric, delta=e.delta, scope=e.scope,
                                        district_id=e.district_id,
                                    ) for e in de.effects],
                                ) for de in template.delayed_effects
                            ],
                            duration_penalty_per_day=template.duration_penalty_per_day,
                            duration_penalty_metric=template.duration_penalty_metric,
                            cascade_dependency=template.cascade_dependency,
                            cascade_scope=template.cascade_scope,
                            residential_impact=template.residential_impact,
                        )
                        other_building.fail(tick, dup_id)
                        other_building.hidden_failure = True
                        new_events.append(dup_event)

    return new_events