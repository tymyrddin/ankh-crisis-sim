"""Remedy application — player actions to address events."""

from __future__ import annotations

import random
from dataclasses import dataclass

from src.config.loader import GameConfig, RemedyConfig
from src.models.city import City
from src.models.event import GameEvent


@dataclass
class RemedyResult:
    success: bool
    message: str
    cost: float = 0
    headline: str = ""


def get_available_remedies(cfg: GameConfig) -> list[RemedyConfig]:
    """Return all remedy types the player can choose from."""
    return list(cfg.remedies.values())


def apply_remedy(
    cfg: GameConfig,
    city: City,
    event: GameEvent,
    remedy_id: str,
    tick: int,
) -> RemedyResult:
    """Apply a remedy to an event. Returns the result."""
    remedy = cfg.remedies.get(remedy_id)
    if not remedy:
        return RemedyResult(success=False, message=f"Unknown remedy: {remedy_id}")

    if not event.is_visible:
        return RemedyResult(success=False, message="Cannot address an undetected event")

    building = city.get_building(event.target_building_id)
    district = city.districts.get(event.target_district_id)

    # Calculate cost
    cost = float(remedy.base_cost)
    if district:
        # Poor infrastructure = more expensive repairs
        cost_raw = remedy.raw.get("cost_modifiers", {})
        if cost_raw.get("infrastructure_quality") == "inverse" and district.infrastructure_quality > 0:
            cost *= 1.0 / district.infrastructure_quality
        if cost_raw.get("district_wealth") == "direct":
            cost *= district.wealth / 50.0  # normalised around median
        if cost_raw.get("population_affected") == "direct":
            cost *= district.density / 100.0

    # Check budget
    if city.budget.value < cost:
        return RemedyResult(
            success=False,
            message=f"Insufficient budget. Need {cost:.0f}, have {city.budget.value:.0f}",
        )

    # Deduct cost
    city.budget.apply(-cost, tick, cause=f"{remedy.label} at {building.name if building else 'unknown'}")

    # Mark event as responding
    event.start_response(remedy_id, tick)

    # Apply immediate trust effects
    trust_raw = remedy.raw.get("trust_effect", {})
    immediate_trust = trust_raw.get("immediate", 0)
    if immediate_trust and district:
        district.local_trust.apply(immediate_trust, tick, cause=remedy.label)

    # Regulatory pressure effects
    reg_decrease = remedy.raw.get("regulatory_pressure_decrease", 0)
    if reg_decrease:
        city.regulatory_pressure.apply(-reg_decrease, tick, cause=remedy.label)

    # Handle backfire risk for accountability
    backfire_risk = trust_raw.get("backfire_risk", 0)
    if backfire_risk > 0 and random.random() < backfire_risk:
        penalty = trust_raw.get("backfire_penalty", -5)
        if district:
            district.local_trust.apply(penalty, tick, cause=f"{remedy.label} backfired")
        city.public_trust.apply(penalty, tick, cause=f"{remedy.label} backfired")

    # Schedule resolution after downtime
    if remedy.downtime_hours == 0:
        _resolve_event(cfg, city, event, remedy, building, tick)
    # else: resolution happens in simulation.py after downtime_hours

    headline = ""
    headlines_raw = cfg.headlines_raw.get("remedy_applied", {})
    template = headlines_raw.get(remedy_id, "")
    if template and building:
        headline = template.format(
            building=building.name,
            district=district.name if district else "",
        )

    return RemedyResult(
        success=True,
        message=f"{remedy.label} applied",
        cost=cost,
        headline=headline,
    )


def process_remedy_completions(
    cfg: GameConfig,
    city: City,
    tick: int,
) -> list[tuple[str, GameEvent]]:
    """Check for remedies that have completed their downtime.

    Returns list of (message, resolved_event) tuples.
    """
    completed: list[tuple[str, GameEvent]] = []
    for event in city.active_events:
        if event.remedy_applied is None:
            continue
        remedy = cfg.remedies.get(event.remedy_applied)
        if not remedy:
            continue
        if event.remedy_applied_tick is None:
            continue

        hours_since_remedy = tick - event.remedy_applied_tick
        if hours_since_remedy >= remedy.downtime_hours:
            building = city.get_building(event.target_building_id)
            _resolve_event(cfg, city, event, remedy, building, tick)
            completed.append((f"{event.name} resolved via {remedy.label}", event))

    return completed


def _resolve_event(
    cfg: GameConfig,
    city: City,
    event: GameEvent,
    remedy: RemedyConfig,
    building,
    tick: int,
) -> None:
    """Complete resolution of an event."""
    event.resolve(tick)

    if building:
        building.restore(recurrence_risk=remedy.recurrence_risk)

    # Infrastructure quality boost (resilience investment)
    if remedy.infrastructure_quality_boost > 0:
        district = city.districts.get(event.target_district_id)
        if district:
            district.infrastructure_quality = min(
                1.0, district.infrastructure_quality + remedy.infrastructure_quality_boost
            )