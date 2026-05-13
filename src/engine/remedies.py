"""Remedy application: player actions to address events."""

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
    """Return remedies the player can choose from for the given event.

    The threatmodel restricts each of the four named recovery pathways to
    specific domains via a `valid_domains` list in `config/remedies.yml`.
    Meta-options (press_statement, operational_workaround, do_nothing) carry
    no `valid_domains` entry and are always available.

    Calling with no event preserves the old "all remedies" behaviour for
    contexts that just need the catalogue.
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
        # Residential-impact events must additionally satisfy the residential
        # row in the threatmodel: only pathways that list "residential" in
        # valid_domains are offered. The intersection of (event.domain) and
        # ("residential") is what the threatmodel actually constrains.
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

    # Trust decay multiplier: immediate signal when inaction is chosen (do_nothing)
    decay_mult = trust_raw.get("decay_multiplier", 0)
    if decay_mult > 1.0 and district:
        # Each unit above 1.0 adds an immediate trust penalty — citizens see the abandonment
        district.local_trust.apply(-(decay_mult - 1.0) * 3, tick, cause=f"{remedy.label} (inaction)")

    # Side effects: political_stability_delta, cascade_risk_increase, risk_transfer, etc.
    for side_effect in remedy.raw.get("side_effects", []):
        delta = side_effect.get("political_stability_delta")
        if delta is not None:
            city.political_stability.apply(float(delta), tick, cause=remedy.label)
        boost = side_effect.get("cascade_risk_increase")
        if boost is not None:
            event.cascade_risk_boost = float(boost)
        if side_effect.get("risk_transfer"):
            # Workaround: the burden shifts to another district
            shifted_penalty = trust_raw.get("shifted_district_penalty", 0)
            if shifted_penalty:
                others = [d for d in city.districts.values() if d.id != event.target_district_id]
                if others:
                    target_district = random.choice(others)
                    target_district.local_trust.apply(
                        float(shifted_penalty), tick, cause=f"{remedy.label} burden transferred"
                    )

    # public_compensation: trust boost fades after duration_days (reversal scheduled as DelayedEffect)
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

    # Social inequality shift: track whether wealthy or poor districts are prioritised.
    # Applying any remedy to a high-wealth district concentrates resource attention there;
    # resilience investment in a low-wealth district actively reduces inequality.
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

    # Compute and cache effective downtime (committed at application time, displayed to the player).
    # underinvestment.extends_recovery_time and org_fragmentation.delays_response multiply the base.
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

    # Narrative-effects accumulation: any remedy whose trust_effect declares
    # contradicts_penalty is a "window" remedy (press_statement and any future
    # equivalent) and increments the narrative counter on application.
    if trust_raw.get("contradicts_penalty") is not None:
        increment_narrative_effects(city, cfg, "press_statement")

    # Schedule resolution after downtime.
    # Window remedies (any remedy with contradicts_penalty) stay in RESPONDING
    # for duration_hours; see process_remedy_completions. All other zero-downtime
    # remedies resolve immediately.
    if remedy.downtime_hours == 0 and trust_raw.get("contradicts_penalty") is None:
        _resolve_event(cfg, city, event, remedy, building, tick)
    # else: resolution (or expiry) handled by process_remedy_completions

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

        # --- Narrative-window remedy expiry (press_statement and equivalents) ---
        # A remedy whose trust_effect declares a `contradicts_penalty` is a
        # "window" remedy: downtime_hours=0 but it stays in RESPONDING for
        # duration_hours. When the window closes without a real remedy
        # following, apply the contradicts_penalty and revert the event to
        # DETECTED so the player has to deal with it properly. Data-driven so
        # future window-style remedies need no code change.
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
                # Narrative effects: contradicts penalty raises the counter
                increment_narrative_effects(city, cfg, "contradicts")
                # Revert to DETECTED so the problem remains
                event.phase = EventPhase.DETECTED
                event.remedy_applied = None
                event.remedy_applied_tick = None
                completed.append((f"{event.name}: no action followed {remedy.label.lower()}", event))
            continue  # never treated as a normal downtime completion

        # Effective downtime was committed and cached at remedy application time.
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
    """Complete resolution of an event."""
    event.resolve(tick)

    if building:
        building.restore(recurrence_risk=remedy.recurrence_risk)

    # Infrastructure quality improvement (resilience investment).
    # infrastructure_quality IS the failure-probability multiplier (3.0 = 3x as likely).
    # A resilience upgrade reduces it multiplicatively toward baseline: each upgrade
    # cuts the excess above 1.0 by `boost` fraction, regardless of starting value.
    # Examples with boost=0.3 per upgrade:
    #   Shades (3.0) → 2.4 → 1.9 → 1.5 → 1.2 → 1.0  (five upgrades to reach baseline)
    #   Isle of Gods (1.5) → 1.2 → 1.0  (two upgrades)
    #   Nap Hill (0.3) → unchanged (already better than baseline)
    if remedy.infrastructure_quality_boost > 0:
        district = city.districts.get(event.target_district_id)
        if district and district.infrastructure_quality > 1.0:
            excess = district.infrastructure_quality - 1.0
            reduction = excess * remedy.infrastructure_quality_boost
            district.infrastructure_quality = max(1.0, district.infrastructure_quality - reduction)

    # Stressor decrease side effects (e.g., resilience_investment reduces underinvestment)
    for side_effect in remedy.raw.get("side_effects", []):
        decrease = side_effect.get("stressor_decrease")
        if decrease and isinstance(decrease, dict):
            for stressor_id, amount in decrease.items():
                current = city.stressors.get(stressor_id, 0.0)
                city.stressors[stressor_id] = max(0.0, current - float(amount))

    # Trust recovery at resolution: citizens see the completed improvement.
    # If trust_effect.delayed_days is set, the trust gain is deferred (workers finish,
    # but neighbours only notice the improvement once it's been running a while).
    # Political stability gain fires immediately regardless.
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