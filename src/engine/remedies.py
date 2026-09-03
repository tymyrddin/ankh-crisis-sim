from __future__ import annotations

import random
from dataclasses import dataclass

from src.config.loader import GameConfig, RemedyConfig
from src.engine.metrics import increment_narrative_effects
from src.models.city import City
from src.models.event import DelayedEffect, EventPhase, GameEvent, MetricEffect


@dataclass
class RemedyResult:
    success: bool
    message: str
    cost: float = 0
    headline: str = ""


def get_available_remedies(
    cfg: GameConfig,
    event: GameEvent | None = None,
) -> list[RemedyConfig]:
    """Remedies offered for an event, or the whole catalogue when there is none.

    valid_domains in remedies.yml restricts the four named pathways; the
    universals carry no such list and always appear.
    """
    all_remedies = list(cfg.remedies.values())
    if event is None or not event.domain:
        return all_remedies

    filtered: list[RemedyConfig] = []
    for remedy in all_remedies:
        valid_domains = remedy.raw.get("valid_domains")
        if not valid_domains:
            filtered.append(remedy)
            continue
        if event.domain not in valid_domains:
            continue
        # residential-impact events also need "residential" in valid_domains
        if event.residential_impact and "residential" not in valid_domains:
            continue
        filtered.append(remedy)
    return filtered


def apply_remedy(
    cfg: GameConfig,
    city: City,
    event: GameEvent,
    remedy_id: str,
    tick: int,
) -> RemedyResult:
    remedy = cfg.remedies.get(remedy_id)
    if not remedy:
        return RemedyResult(success=False, message=f"Unknown remedy: {remedy_id}")

    if not event.is_visible:
        return RemedyResult(success=False, message="Cannot address an undetected event")

    building = city.get_building(event.target_building_id)
    district = city.districts.get(event.target_district_id)

    cost = float(remedy.base_cost)
    if district:
        cost_raw = remedy.raw.get("cost_modifiers", {})
        # infrastructure_quality is the failure multiplier, so worse districts pay more
        if cost_raw.get("infrastructure_quality") == "inverse" and district.infrastructure_quality > 0:
            cost *= district.infrastructure_quality
        if cost_raw.get("district_wealth") == "direct":
            cost *= district.wealth / 50.0  # 50 is the median
        if cost_raw.get("population_affected") == "direct":
            cost *= district.density / 100.0

    # may run into the red, down to the configured floor
    if city.budget.value - cost < city.budget.min_value:
        return RemedyResult(
            success=False,
            message=(
                f"Insufficient budget and credit. Need {cost:.0f}, have {city.budget.value:.0f} "
                f"(credit floor {city.budget.min_value:.0f})"
            ),
        )

    city.budget.apply(-cost, tick, cause=f"{remedy.label} at {building.name if building else 'unknown'}")

    event.start_response(remedy_id, tick)

    trust_raw = remedy.raw.get("trust_effect", {})
    immediate_trust = trust_raw.get("immediate", 0)
    if immediate_trust and district:
        district.local_trust.apply(immediate_trust, tick, cause=remedy.label)

    reg_decrease = remedy.raw.get("regulatory_pressure_decrease", 0)
    if reg_decrease:
        city.regulatory_pressure.apply(-reg_decrease, tick, cause=remedy.label)

    backfire_risk = trust_raw.get("backfire_risk", 0)
    if backfire_risk > 0 and random.random() < backfire_risk:
        penalty = trust_raw.get("backfire_penalty", -5)
        if district:
            district.local_trust.apply(penalty, tick, cause=f"{remedy.label} backfired")
        city.public_trust.apply(penalty, tick, cause=f"{remedy.label} backfired")

    # do_nothing: each unit of decay_multiplier above 1.0 is an immediate trust hit
    decay_mult = trust_raw.get("decay_multiplier", 0)
    if decay_mult > 1.0 and district:
        district.local_trust.apply(-(decay_mult - 1.0) * 3, tick, cause=f"{remedy.label} (inaction)")

    for side_effect in remedy.raw.get("side_effects", []):
        delta = side_effect.get("political_stability_delta")
        if delta is not None:
            city.political_stability.apply(float(delta), tick, cause=remedy.label)
        boost = side_effect.get("cascade_risk_increase")
        if boost is not None:
            event.cascade_risk_boost = float(boost)
        if side_effect.get("risk_transfer"):
            # the burden lands on another district
            shifted_penalty = trust_raw.get("shifted_district_penalty", 0)
            if shifted_penalty:
                others = [d for d in city.districts.values() if d.id != event.target_district_id]
                if others:
                    target_district = random.choice(others)
                    target_district.local_trust.apply(
                        float(shifted_penalty), tick, cause=f"{remedy.label} burden transferred"
                    )

    # a temporary trust boost reverses after duration_days
    duration_days = trust_raw.get("duration_days", 0)
    if duration_days > 0 and immediate_trust and district:
        delay_hours = int(duration_days * 24) + (tick - event.created_tick)
        event.delayed_effects.append(DelayedEffect(
            delay_hours=delay_hours,
            effects=[MetricEffect(
                metric="local_trust",
                delta=-float(immediate_trust),
                scope="district",
                district_id=event.target_district_id,
            )],
        ))

    # spending in rich districts widens inequality; resilience investment in poor ones narrows it
    inequality_sc = cfg.stressors.get("social_inequality")
    if inequality_sc and district:
        change_rate = inequality_sc.raw.get("change_rate", {})
        current = city.stressors.get("social_inequality", 0.0)
        if district.wealth_archetype == "high_wealth":
            rate = change_rate.get("inequality_increase", 0)
            if rate:
                city.stressors["social_inequality"] = min(1.0, current + float(rate))
        elif district.wealth_archetype == "low_wealth" and remedy_id == "resilience_investment":
            rate = change_rate.get("inequality_decrease", 0)
            if rate:
                city.stressors["social_inequality"] = max(0.0, current - float(rate))

    # downtime is fixed now; extends_recovery_time and delays_response stretch it
    effective_downtime = float(remedy.downtime_hours)
    if effective_downtime > 0:
        for sc in cfg.stressors.values():
            level = city.stressors.get(sc.id, 0.0)
            for effect in sc.raw.get("effects", []):
                ert = effect.get("extends_recovery_time")
                if ert is not None:
                    effective_downtime *= 1.0 + (float(ert) - 1.0) * level
                dr = effect.get("delays_response")
                if dr is not None:
                    effective_downtime *= 1.0 + (float(dr) - 1.0) * level
    event.effective_downtime_hours = effective_downtime

    # a remedy with contradicts_penalty is a window remedy (press_statement)
    if trust_raw.get("contradicts_penalty") is not None:
        increment_narrative_effects(city, cfg, "press_statement")

    # zero-downtime remedies resolve now; window remedies wait for process_remedy_completions
    if remedy.downtime_hours == 0 and trust_raw.get("contradicts_penalty") is None:
        _resolve_event(cfg, city, event, remedy, building, tick)

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

        # window remedy expired with nothing real behind it: penalty, then back to DETECTED
        trust_raw = remedy.raw.get("trust_effect", {})
        if trust_raw.get("contradicts_penalty") is not None:
            window = trust_raw.get("duration_hours", 48)
            if hours_since_remedy >= window:
                penalty = trust_raw.get("contradicts_penalty", 0)
                district = city.districts.get(event.target_district_id)
                if penalty and district:
                    district.local_trust.apply(
                        float(penalty), tick, cause=f"{remedy.label} contradicted by inaction"
                    )
                increment_narrative_effects(city, cfg, "contradicts")
                event.phase = EventPhase.DETECTED
                event.remedy_applied = None
                event.remedy_applied_tick = None
                completed.append((f"{event.name}: no action followed {remedy.label.lower()}", event))
            continue

        effective_downtime = event.effective_downtime_hours
        if effective_downtime is None:
            effective_downtime = float(remedy.downtime_hours)

        if hours_since_remedy >= effective_downtime:
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
    event.resolve(tick)

    if building:
        building.restore(recurrence_risk=remedy.recurrence_risk)

    # each upgrade cuts the excess above baseline 1.0 by boost; the Shades at 3.0 need five
    if remedy.infrastructure_quality_boost > 0:
        district = city.districts.get(event.target_district_id)
        if district and district.infrastructure_quality > 1.0:
            excess = district.infrastructure_quality - 1.0
            reduction = excess * remedy.infrastructure_quality_boost
            district.infrastructure_quality = max(1.0, district.infrastructure_quality - reduction)

    for side_effect in remedy.raw.get("side_effects", []):
        decrease = side_effect.get("stressor_decrease")
        if decrease and isinstance(decrease, dict):
            for stressor_id, amount in decrease.items():
                current = city.stressors.get(stressor_id, 0.0)
                city.stressors[stressor_id] = max(0.0, current - float(amount))

    # delayed_days defers the trust gain; the stability gain lands now
    trust_raw = remedy.raw.get("trust_effect", {})
    resolution_amount = trust_raw.get("amount", 0)
    if resolution_amount:
        district = city.districts.get(event.target_district_id)
        delayed_days = trust_raw.get("delayed_days", 0)
        if district:
            if delayed_days > 0:
                apply_at = tick + int(delayed_days * 24)
                district.pending_trust_boosts.append(
                    (apply_at, resolution_amount, f"{remedy.label} completed")
                )
            else:
                district.local_trust.apply(resolution_amount, tick, cause=f"{remedy.label} completed")
        stability_gain = resolution_amount * 0.15
        city.political_stability.apply(stability_gain, tick, cause=f"{remedy.label} completed")