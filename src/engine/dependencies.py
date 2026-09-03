from __future__ import annotations

import random
import uuid

from src.models.building import Building
from src.models.city import City
from src.models.event import EventPhase, GameEvent, MetricEffect


def _find_dependent_buildings(
    city: City,
    failed_building: Building,
    dependency_type: str,
    scope: str,
) -> list[Building]:
    dependents = []

    if scope == "neighbours":
        district = city.districts.get(failed_building.district_id)
        if not district:
            return []
        candidates = district.buildings.values()
    else:
        candidates = []
        for d in city.districts.values():
            candidates.extend(d.buildings.values())

    for building in candidates:
        if building.id == failed_building.id:
            continue
        if building.is_failed:
            continue
        all_deps = building.dependencies.critical + building.dependencies.operational
        if dependency_type in all_deps:
            dependents.append(building)

    return dependents


def propagate_cascades(
    city: City,
    tick: int,
    ticks_per_day: int = 24,
    cascade_multiplier: float = 1.0,
    domain_multipliers: dict[str, float] | None = None,
) -> list[GameEvent]:
    """Roll cascades for detected, unattended events: once per day per event, from the detection tick."""
    cascade_events = []

    for event in city.active_events:
        if not event.cascade_dependency:
            continue
        if not event.is_visible:
            continue
        if event.phase == EventPhase.RESPONDING:
            continue  # a response in progress shields dependents

        hours_since_detected = tick - (event.detected_tick or event.created_tick)
        if hours_since_detected % ticks_per_day != 0:
            continue

        failed_building = city.get_building(event.target_building_id)
        if not failed_building:
            continue

        # domain multipliers scale the trust hit, not the odds, so event counts stay balanced
        cascade_trust_delta = -3.0
        if domain_multipliers and event.domain in domain_multipliers:
            cascade_trust_delta *= domain_multipliers[event.domain]

        # vendor monoculture can widen a local cascade to the whole city; the odds equal the level
        effective_scope = event.cascade_scope
        vendor_mono = city.stressors.get("vendor_monoculture", 0.0)
        if vendor_mono > 0 and effective_scope == "neighbours" and random.random() < vendor_mono:
            effective_scope = "city"

        dependents = _find_dependent_buildings(
            city, failed_building, event.cascade_dependency, effective_scope
        )

        for dep_building in dependents:
            is_critical = event.cascade_dependency in dep_building.dependencies.critical
            cascade_prob = 0.3 if is_critical else 0.1
            cascade_prob *= cascade_multiplier * event.cascade_risk_boost

            district = city.get_district_for_building(dep_building.id)
            if district:
                cascade_prob *= district.failure_probability_modifier

            cascade_prob = min(cascade_prob, 0.95)  # never a certainty

            if random.random() >= cascade_prob:
                continue

            cascade_id = f"cascade_{event.id}_{uuid.uuid4().hex[:6]}"
            cascade_event = GameEvent(
                id=cascade_id,
                template_id=f"cascade_{event.template_id}",
                name=f"Cascade: {dep_building.name} affected",
                category=event.category,
                domain=event.domain,
                phase=EventPhase.DETECTED,  # cascades are never hidden
                target_district_id=dep_building.district_id,
                target_building_id=dep_building.id,
                created_tick=tick,
                detected_tick=tick,
                immediate_effects=[MetricEffect(
                    metric="local_trust",
                    delta=cascade_trust_delta,
                    scope="district",
                    district_id=dep_building.district_id,
                )],
                headline=f"{dep_building.name} affected by {event.domain} failure",
            )

            dep_building.fail(tick, cascade_id)
            dep_building.hidden_failure = False
            cascade_events.append(cascade_event)

    return cascade_events