"""Dependency graph — cascading failures propagate through building relationships."""

from __future__ import annotations

import random
import uuid

from src.models.building import Building, BuildingStatus
from src.models.city import City
from src.models.event import EventPhase, GameEvent, MetricEffect


def _find_dependent_buildings(
    city: City,
    failed_building: Building,
    dependency_type: str,
    scope: str,
) -> list[Building]:
    """Find buildings that depend on the failed building's domain."""
    dependents = []

    if scope == "neighbours":
        # Only buildings in the same district
        district = city.districts.get(failed_building.district_id)
        if not district:
            return []
        candidates = district.buildings.values()
    else:
        # All buildings in the city
        candidates = []
        for d in city.districts.values():
            candidates.extend(d.buildings.values())

    for building in candidates:
        if building.id == failed_building.id:
            continue
        if building.is_failed:
            continue  # already failed
        # Check if this building has the failed dependency in critical or operational
        all_deps = building.dependencies.critical + building.dependencies.operational
        if dependency_type in all_deps:
            dependents.append(building)

    return dependents


def propagate_cascades(
    city: City,
    tick: int,
) -> list[GameEvent]:
    """For each active event with cascade rules, potentially fail dependent buildings."""
    cascade_events = []

    for event in city.active_events:
        if not event.cascade_dependency:
            continue
        if not event.is_visible:
            continue  # cascades only from detected events

        failed_building = city.get_building(event.target_building_id)
        if not failed_building:
            continue

        dependents = _find_dependent_buildings(
            city, failed_building, event.cascade_dependency, event.cascade_scope
        )

        for dep_building in dependents:
            # Probability of cascade: based on whether dependency is critical
            is_critical = event.cascade_dependency in dep_building.dependencies.critical
            cascade_prob = 0.3 if is_critical else 0.1

            # Infrastructure quality reduces cascade probability
            district = city.get_district_for_building(dep_building.id)
            if district:
                cascade_prob *= district.failure_probability_modifier

            if random.random() >= cascade_prob:
                continue

            # Create cascade event
            cascade_id = f"cascade_{event.id}_{uuid.uuid4().hex[:6]}"
            cascade_event = GameEvent(
                id=cascade_id,
                template_id=f"cascade_{event.template_id}",
                name=f"Cascade: {dep_building.name} affected",
                category=event.category,
                domain=event.domain,
                phase=EventPhase.DETECTED,  # cascades are immediately visible
                target_district_id=dep_building.district_id,
                target_building_id=dep_building.id,
                created_tick=tick,
                detected_tick=tick,
                immediate_effects=[MetricEffect(
                    metric="local_trust",
                    delta=-3,
                    scope="district",
                    district_id=dep_building.district_id,
                )],
                headline=f"{dep_building.name} affected by {event.domain} failure",
            )

            dep_building.fail(tick, cascade_id)
            dep_building.hidden_failure = False
            cascade_events.append(cascade_event)

    return cascade_events