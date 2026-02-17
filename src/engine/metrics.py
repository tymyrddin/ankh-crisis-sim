"""Metrics engine — applies effects to city and district metrics each tick."""

from __future__ import annotations

from src.config.loader import GameConfig
from src.models.city import City
from src.models.event import GameEvent, MetricEffect


def apply_immediate_effects(
    city: City,
    event: GameEvent,
    tick: int,
) -> None:
    """Apply an event's immediate metric effects."""
    for effect in event.immediate_effects:
        _apply_effect(city, effect, tick, cause=event.name)


def apply_delayed_effects(
    city: City,
    tick: int,
) -> list[str]:
    """Check all active events for delayed effects that are now due. Returns descriptions."""
    applied = []
    for event in city.active_events:
        for delayed in event.delayed_effects:
            if delayed.applied:
                continue
            hours_since = tick - event.created_tick
            if hours_since >= delayed.delay_hours:
                for effect in delayed.effects:
                    _apply_effect(city, effect, tick, cause=f"{event.name} (delayed)")
                delayed.applied = True
                applied.append(f"Delayed effects of {event.name}")
    return applied


def apply_duration_penalties(
    city: City,
    tick: int,
    ticks_per_day: int,
) -> None:
    """Apply ongoing penalties for unresolved events (per-day basis)."""
    for event in city.active_events:
        if event.duration_penalty_per_day == 0:
            continue
        hours_active = tick - event.created_tick
        # Apply penalty once per day
        if hours_active > 0 and hours_active % ticks_per_day == 0:
            effect = MetricEffect(
                metric=event.duration_penalty_metric,
                delta=event.duration_penalty_per_day,
                scope="district",
                district_id=event.target_district_id,
            )
            _apply_effect(city, effect, tick, cause=f"{event.name} (duration)")


def apply_income(
    city: City,
    cfg: GameConfig,
    tick: int,
    ticks_per_day: int,
) -> None:
    """Apply monthly income to budget. Called once per 30-day cycle."""
    days = tick // ticks_per_day
    if days == 0 or tick % (ticks_per_day * 30) != 0:
        return

    total_income = 0.0
    for source, amount in cfg.budget_income.items():
        if isinstance(amount, (int, float)):
            total_income += amount

    # Trust penalty on tax collection
    trust_threshold = cfg.metrics_global_raw.get("budget", {}).get(
        "income_sources", {}
    ).get("taxes", {}).get("trust_threshold", 30)

    if city.public_trust.value < trust_threshold:
        penalty = cfg.metrics_global_raw.get("budget", {}).get(
            "income_sources", {}
        ).get("taxes", {}).get("penalty_multiplier", 0.6)
        # Only taxes affected
        taxes = cfg.budget_income.get("taxes_general", 350)
        total_income -= taxes * (1 - penalty)

    city.budget.apply(total_income, tick, cause="Monthly income")


def update_global_trust_from_districts(city: City, tick: int) -> None:
    """Recalculate global trust as weighted average of district trust."""
    total_weight = 0.0
    weighted_trust = 0.0

    for district in city.districts.values():
        if not district.is_residential:
            continue
        weight = (district.density + district.political_influence * 100) / 2
        weighted_trust += district.local_trust.value * weight
        total_weight += weight

    if total_weight > 0:
        new_trust = weighted_trust / total_weight
        # Blend: 70% from districts, 30% from existing (smoothing)
        blended = city.public_trust.value * 0.3 + new_trust * 0.7
        city.public_trust.set(blended, tick, cause="District aggregate")


def _apply_effect(
    city: City,
    effect: MetricEffect,
    tick: int,
    cause: str = "",
) -> None:
    """Apply a single metric effect to the appropriate target."""
    if effect.scope == "district" and effect.district_id:
        district = city.districts.get(effect.district_id)
        if district and effect.metric == "local_trust":
            # Apply media attention multiplier
            delta = effect.delta * district.media_attention_multiplier
            district.local_trust.apply(delta, tick, cause=cause)
            return

    # Global metric
    metric = city.get_metric(effect.metric)
    if metric:
        metric.apply(effect.delta, tick, cause=cause)