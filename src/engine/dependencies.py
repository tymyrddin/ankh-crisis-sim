"""Dependency graph: cascading failures propagate through building relationships."""

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
    ticks_per_day: int = 24,
    cascade_multiplier: float = 1.0,
    domain_multipliers: dict[str, float] | None = None,
) -> list[GameEvent]:
    """For each active event with cascade rules, potentially fail dependent buildings.

    Cascades roll once per day per event (not every tick), starting from the
    tick the event was detected. This spreads cascade failures over time.
    """
    cascade_events = []

    for event in city.active_events:
        if not event.cascade_dependency:
            continue
        if not event.is_visible:
            continue  # cascades only from detected events
        if event.phase == EventPhase.RESPONDING:
            continue  # structural repair includes reroutings and workarounds;
                      # dependents are temporarily fed via alternative routes

        # Only roll cascades once per day (at the daily anniversary of detection)
        hours_since_detected = tick - (event.detected_tick or event.created_tick)
        if hours_since_detected == 0:
            pass  # first tick after detection: always roll
        elif hours_since_detected % ticks_per_day != 0:
            continue  # not a daily boundary: skip

        failed_building = city.get_building(event.target_building_id)
        if not failed_building:
            continue

        # Per-domain stressor amplification: just_in_time logistics means cascades
        # hurt MORE per event (no buffer stock to absorb the shock), not more often.
        # Amplifier applied to trust delta, not probability, to preserve event-count balance.
        cascade_trust_delta = -3.0
        if domain_multipliers and event.domain in domain_multipliers:
            cascade_trust_delta *= domain_multipliers[event.domain]

        # vendor_monoculture: single_point_of_failure / multi_district_impact.
        # High monoculture escalates a local cascade to city-wide — every building
        # relying on the same vendor gets hit, not just neighbours.
        # Probability of escalation equals the stressor level (0.7 → 70% chance).
        effective_scope = event.cascade_scope
        vendor_mono = city.stressors.get("vendor_monoculture", 0.0)
        if vendor_mono > 0 and effective_scope == "neighbours" and random.random() < vendor_mono:
            effective_scope = "city"

        dependents = _find_dependent_buildings(
            city, failed_building, event.cascade_dependency, effective_scope
        )

        for dep_building in dependents:
            # Probability of cascade: based on whether dependency is critical.
            # do_nothing raises cascade_risk_boost on the event.
            is_critical = event.cascade_dependency in dep_building.dependencies.critical
            cascade_prob = 0.3 if is_critical else 0.1
            cascade_prob *= cascade_multiplier * event.cascade_risk_boost

            # Infrastructure quality modifies cascade probability
            district = city.get_district_for_building(dep_building.id)
            if district:
                cascade_prob *= district.failure_probability_modifier

            cascade_prob = min(cascade_prob, 0.95)  # never guaranteed even in the worst districts

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