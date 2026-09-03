from __future__ import annotations

import math
from collections.abc import Callable

from src.config.loader import GameConfig
from src.models.city import City
from src.models.event import EventPhase, GameEvent, MetricEffect


def narrative_effects_shaped(raw: float, shape: str = "tanh") -> float:
    """tanh of the raw counter, so early steps show and late ones saturate."""
    if raw <= 0:
        return 0.0
    if shape == "tanh":
        return math.tanh(raw)
    return min(1.0, raw)


def increment_narrative_effects(city: City, cfg: GameConfig, key: str) -> None:
    """key is one of the increments: entries under narrative_effects in stressors.yml."""
    sc = cfg.stressors.get("narrative_effects")
    if not sc:
        return
    increments = sc.raw.get("increments", {})
    delta = float(increments.get(key, 0.0))
    if delta <= 0:
        return
    city.narrative_effects += delta


def apply_immediate_effects(
    city: City,
    event: GameEvent,
    tick: int,
) -> None:
    for effect in event.immediate_effects:
        _apply_effect(city, effect, tick, cause=event.name)


def apply_delayed_effects(
    city: City,
    tick: int,
) -> list[str]:
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
    """Daily penalty for events the player can see and has not answered."""
    for event in city.active_events:
        if event.duration_penalty_per_day == 0:
            continue
        if event.phase != EventPhase.DETECTED:
            continue
        hours_active = tick - event.created_tick
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
    """Monthly income.

    Guild fees, river duties and clacks licensing scale with the buildings still
    standing, tariffs fall per failed transport or food building, and taxes take
    a cut when public trust is below the threshold.
    """
    days = tick // ticks_per_day
    if days == 0 or tick % (ticks_per_day * 30) != 0:
        return

    income_raw = cfg.budget_income
    taxes = float(income_raw.get("taxes_general", 350))
    guild_fees = float(income_raw.get("guild_fees", 200))
    tariffs = float(income_raw.get("trade_tariffs", 150))
    university = float(income_raw.get("university_contribution", 50))

    budget_cfg = _income_sources(cfg)

    if city.public_trust.value < tax_trust_threshold(cfg):
        penalty_mult = budget_cfg.get("taxes", {}).get("penalty_multiplier", 0.6)
        taxes *= penalty_mult

    guild_buildings = [
        b for d in city.districts.values()
        for b in d.buildings.values()
        if b.type_id == "guild_hq"
    ]
    if guild_buildings:
        operational = sum(1 for b in guild_buildings if b.is_operational)
        # the underground economy still pays half
        guild_fees *= 0.5 + 0.5 * (operational / len(guild_buildings))

    disrupted = sum(
        1 for d in city.districts.values()
        for b in d.buildings.values()
        if b.type_id in ("transport", "food_supply") and b.is_failed
    )
    if disrupted > 0:
        disruption_penalty = budget_cfg.get("trade_tariffs", {}).get("disruption_penalty", 0.3)
        tariffs *= max(0.0, 1.0 - disrupted * disruption_penalty)

    river_trade = float(income_raw.get("river_trade_duties", 300))
    trade_buildings = [
        b for d in city.districts.values()
        for b in d.buildings.values()
        if b.type_id in ("transport", "food_supply")
    ]
    if trade_buildings:
        operational_trade = sum(1 for b in trade_buildings if b.is_operational)
        floor_pct = budget_cfg.get("river_trade_duties", {}).get("floor", 0.2)
        river_trade *= floor_pct + (1.0 - floor_pct) * (operational_trade / len(trade_buildings))

    clacks_revenue = float(income_raw.get("clacks_revenue", 0))
    if clacks_revenue > 0:
        clacks_buildings = [
            b for d in city.districts.values()
            for b in d.buildings.values()
            if b.type_id == "clacks_tower"
        ]
        if clacks_buildings:
            operational_clacks = sum(1 for b in clacks_buildings if b.is_operational)
            floor_pct = budget_cfg.get("clacks_revenue", {}).get("floor", 0.1)
            clacks_revenue *= floor_pct + (1.0 - floor_pct) * (operational_clacks / len(clacks_buildings))

    total_income = taxes + guild_fees + tariffs + university + river_trade + clacks_revenue
    city.budget.apply(total_income, tick, cause="Monthly income")


def _income_sources(cfg: GameConfig) -> dict:
    return cfg.metrics_global_raw.get("budget", {}).get("income_sources", {})


def tax_trust_threshold(cfg: GameConfig) -> float:
    """Public trust below this costs tax income and, monthly, feeds the budget-cut stressor drift."""
    return float(_income_sources(cfg).get("taxes", {}).get("trust_threshold", 30))


def update_global_trust_from_districts(city: City, tick: int) -> None:
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
        blended = city.public_trust.value * 0.3 + new_trust * 0.7
        city.public_trust.set(blended, tick, cause="District aggregate")


def apply_passive_dynamics(
    city: City,
    tick: int,
    ticks_per_day: int,
    cfg: GameConfig | None = None,
) -> None:
    """Background drift, evaluated once a day; some parts weekly or monthly."""
    if tick == 0 or tick % ticks_per_day != 0:
        return

    is_week = tick % (ticks_per_day * 7) == 0
    is_month = tick % (ticks_per_day * 30) == 0

    visible = city.visible_events
    detected = [e for e in visible if e.phase == EventPhase.DETECTED]
    responding = [e for e in visible if e.phase == EventPhase.RESPONDING]

    neglected = [
        e for e in detected
        if e.detected_tick is not None and tick - e.detected_tick >= ticks_per_day
    ]

    if detected or responding:
        rise = len(detected) * 1.0 + len(responding) * 0.2
        city.regulatory_pressure.apply(rise, tick, cause="Unresolved incidents")
    elif is_week:
        city.regulatory_pressure.apply(-2.0, tick, cause="Quiet city")

    if city.public_trust.value < 25:
        city.political_stability.apply(-2.0, tick, cause="Trust collapse")
    elif is_week and not visible:
        city.political_stability.apply(1.0, tick, cause="Stable period")

    if is_month and city.political_stability.value > 50:
        city.legitimacy.apply(0.5, tick, cause="Sustained governance")

    coverage = city.watch_coverage_pct
    if coverage < 50:
        crime_rise = (50.0 - coverage) / 50.0 * 0.3
        city.crime_level.apply(crime_rise, tick, cause="Reduced Watch coverage")
    elif coverage >= 80:
        city.crime_level.apply(-0.1, tick, cause="Strong Watch presence")

    # Scandal. Ignored events compound daily; organisational fragmentation makes each one worse,
    # and a standing press statement mutes it.
    scandal_org_frag_mult = 1.0
    if cfg:
        org_frag_level = city.stressors.get("organisational_fragmentation", 0.0)
        org_frag_sc = cfg.stressors.get("organisational_fragmentation")
        if org_frag_sc:
            for effect in org_frag_sc.raw.get("effects", []):
                atd = effect.get("accelerates_trust_decay")
                if atd is not None:
                    scandal_org_frag_mult = 1.0 + (float(atd) - 1.0) * org_frag_level
                    break

    narrative_mult = 1.0
    if cfg:
        ne_sc = cfg.stressors.get("narrative_effects")
        if ne_sc:
            raw = city.narrative_effects
            shape = "tanh"
            amp = 0.0
            for eff in ne_sc.raw.get("effects", []):
                if "shape" in eff:
                    shape = eff["shape"]
                if "trust_decay_amplifier" in eff:
                    amp = float(eff["trust_decay_amplifier"])
            narrative_mult = 1.0 + narrative_effects_shaped(raw, shape) * amp

    for event in neglected:
        district = city.districts.get(event.target_district_id)
        if not district:
            continue
        muted = _statement_mute(cfg, event)
        scandal_damage = (
            -1.5 * district.media_attention_multiplier
            * scandal_org_frag_mult * narrative_mult * muted
        )
        label = "muted scandal" if muted < 1.0 else "scandal"
        district.local_trust.apply(scandal_damage, tick, cause=f"{event.name} ({label})")
        if cfg:
            increment_narrative_effects(city, cfg, "scandal")

    for district in city.districts.values():
        due = [entry for entry in district.scheduled_trust_changes if tick >= entry[0]]
        if due:
            district.scheduled_trust_changes = [
                entry for entry in district.scheduled_trust_changes if tick < entry[0]
            ]
            for _, amt, cause in due:
                district.local_trust.apply(amt, tick, cause=cause)

    if cfg:
        trust_floor = tax_trust_threshold(cfg)
        for stressor_id, sc in cfg.stressors.items():
            change_rate = sc.raw.get("change_rate", {})
            if not change_rate:
                continue

            neglect_rate = change_rate.get("neglect_increase")
            if neglect_rate and neglected:
                current = city.stressors.get(stressor_id, 0.0)
                city.stressors[stressor_id] = min(1.0, current + float(neglect_rate))

            budget_cut_rate = change_rate.get("budget_cut_increase")
            if budget_cut_rate and is_month and city.public_trust.value < trust_floor:
                current = city.stressors.get(stressor_id, 0.0)
                city.stressors[stressor_id] = min(1.0, current + float(budget_cut_rate))


def _statement_mute(cfg: GameConfig | None, event: GameEvent) -> float:
    if not cfg or not event.statement_remedy:
        return 1.0
    remedy = cfg.remedies.get(event.statement_remedy)
    if not remedy:
        return 1.0
    slows = remedy.raw.get("trust_effect", {}).get("slows_decay_multiplier")
    return float(slows) if slows is not None else 1.0


def _apply_effect(
    city: City,
    effect: MetricEffect,
    tick: int,
    cause: str = "",
) -> None:
    if effect.scope == "district" and effect.district_id:
        district = city.districts.get(effect.district_id)
        if district and effect.metric == "local_trust":
            delta = effect.delta * district.media_attention_multiplier
            # harsher on victim districts, softer on beneficiaries
            if delta < 0:
                delta *= _inequality_modifier(
                    district.stressors.get("social_inequality"),
                    city.stressors.get("social_inequality", 0.0),
                )
            district.local_trust.apply(delta, tick, cause=cause)
            return

    metric = city.get_metric(effect.metric)
    if metric:
        metric.apply(effect.delta, tick, cause=cause)


# applied to negative trust deltas only
_INEQUALITY_MODIFIERS: dict[str, Callable[[float], float]] = {
    "victim": lambda lvl: 1.0 + lvl * 0.8,
    "moderate": lambda lvl: 1.0 + lvl * 0.3,
    "beneficiary": lambda lvl: max(0.3, 1.0 - lvl * 0.4),
}


def _inequality_modifier(label: str | None, global_level: float) -> float:
    if label is None:
        return 1.0
    fn = _INEQUALITY_MODIFIERS.get(label)
    return fn(global_level) if fn else 1.0
