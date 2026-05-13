"""Metrics engine: applies effects to city and district metrics each tick."""

from __future__ import annotations

import math

from src.config.loader import GameConfig
from src.models.city import City
from src.models.event import EventPhase, GameEvent, MetricEffect


def narrative_effects_shaped(raw: float, shape: str = "tanh") -> float:
    """Map the raw narrative-effects counter to a 0-1 display/multiplier value.

    The raw counter accumulates linearly without decay. The shaped view is what
    mechanics and the GUI consume so the early steps register as visible and
    late steps saturate rather than running away.
    """
    if raw <= 0:
        return 0.0
    if shape == "tanh":
        return math.tanh(raw)
    # Linear clamp fallback
    return min(1.0, raw)


def increment_narrative_effects(city: City, cfg: GameConfig, key: str) -> None:
    """Increase the narrative_effects raw counter by the configured increment.

    `key` matches one of the keys under `increments:` in `narrative_effects`
    in stressors.yml (e.g. 'press_statement', 'contradicts', 'scandal').
    No-op if narrative_effects is not configured.
    """
    sc = cfg.stressors.get("narrative_effects")
    if not sc:
        return
    increments = sc.raw.get("increments", {})
    delta = float(increments.get(key, 0.0))
    if delta <= 0:
        return
    current = city.stressors.get("narrative_effects", 0.0)
    city.stressors["narrative_effects"] = current + delta


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
    """Apply ongoing penalties for unresolved events (per-day basis).

    Penalties only fire while an event is DETECTED (ignored).  Once a remedy
    is in progress (RESPONDING), the active response suspends the daily penalty
    — investing in structural repair should not be punished more than doing
    nothing.  The penalty resumes if the response somehow stalls.
    """
    for event in city.active_events:
        if event.duration_penalty_per_day == 0:
            continue
        if event.phase == EventPhase.RESPONDING:
            continue  # remedy in progress; penalty suspended
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
    """Apply monthly income to budget. Called once per 30-day cycle.

    Guild fees scale with how many guild buildings are operational.
    Trade tariffs are reduced by each failed transport or food-supply building.
    Tax collection is penalised when public trust is very low.
    """
    days = tick // ticks_per_day
    if days == 0 or tick % (ticks_per_day * 30) != 0:
        return

    income_raw = cfg.budget_income
    taxes = float(income_raw.get("taxes_general", 350))
    guild_fees = float(income_raw.get("guild_fees", 200))
    tariffs = float(income_raw.get("trade_tariffs", 150))
    university = float(income_raw.get("university_contribution", 50))

    budget_cfg = cfg.metrics_global_raw.get("budget", {}).get("income_sources", {})

    # --- Tax collection penalty when trust is very low ---
    trust_threshold = budget_cfg.get("taxes", {}).get("trust_threshold", 30)
    if city.public_trust.value < trust_threshold:
        penalty_mult = budget_cfg.get("taxes", {}).get("penalty_multiplier", 0.6)
        taxes *= penalty_mult

    # --- Guild fees: scale with operational guild buildings ---
    guild_buildings = [
        b for d in city.districts.values()
        for b in d.buildings.values()
        if b.type_id == "guild_hq"
    ]
    if guild_buildings:
        operational = sum(1 for b in guild_buildings if b.is_operational)
        # Floor at 50%: underground economy still pays something even when guilds collapse
        guild_fees *= 0.5 + 0.5 * (operational / len(guild_buildings))

    # --- Trade tariffs: reduced by each failed transport or food-supply building ---
    disrupted = sum(
        1 for d in city.districts.values()
        for b in d.buildings.values()
        if b.type_id in ("transport", "food_supply") and b.is_failed
    )
    if disrupted > 0:
        disruption_penalty = budget_cfg.get("trade_tariffs", {}).get("disruption_penalty", 0.3)
        tariffs *= max(0.0, 1.0 - disrupted * disruption_penalty)

    # --- River trade duties: port and wharfage on goods arriving via river and road ---
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

    # --- Clacks revenue: Grand Trunk licensing fees; scales with operational clacks towers ---
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


def apply_passive_dynamics(
    city: City,
    tick: int,
    ticks_per_day: int,
    cfg: GameConfig | None = None,
) -> None:
    """Background metric drift: relationships not driven by individual events.

    All mechanics fire at daily resolution. Some also have weekly or monthly cycles.
    Called every tick but does nothing unless a full day has elapsed.
    """
    if tick == 0 or tick % ticks_per_day != 0:
        return

    is_week = tick % (ticks_per_day * 7) == 0
    is_month = tick % (ticks_per_day * 30) == 0

    visible = city.visible_events
    detected = [e for e in visible if e.phase == EventPhase.DETECTED]
    responding = [e for e in visible if e.phase == EventPhase.RESPONDING]

    # Events ignored for more than 24h (eligible for neglect-driven stressor drift)
    neglected = [
        e for e in detected
        if e.detected_tick is not None and tick - e.detected_tick >= ticks_per_day
    ]

    # ------------------------------------------------------------------
    # 1. Regulatory pressure: rises with unresolved crises; falls when quiet
    # ------------------------------------------------------------------
    if detected or responding:
        # Unresponded events build pressure faster than ones being addressed
        rise = len(detected) * 1.0 + len(responding) * 0.2
        city.regulatory_pressure.apply(rise, tick, cause="Unresolved incidents")
    elif is_week:
        # A full quiet week earns a modest release of pressure
        city.regulatory_pressure.apply(-2.0, tick, cause="Quiet city")

    # ------------------------------------------------------------------
    # 2. Trust → political stability cascade
    # ------------------------------------------------------------------
    if city.public_trust.value < 25:
        # Critical trust collapse destabilises politics every day
        city.political_stability.apply(-2.0, tick, cause="Trust collapse")
    elif is_week and not visible:
        # A stable, incident-free week slowly restores confidence
        city.political_stability.apply(1.0, tick, cause="Stable period")

    # ------------------------------------------------------------------
    # 3. Legitimacy slow passive recovery
    # ------------------------------------------------------------------
    if is_month and city.political_stability.value > 50:
        # Long-term stable governance earns legitimacy back very slowly
        city.legitimacy.apply(0.5, tick, cause="Sustained governance")

    # ------------------------------------------------------------------
    # 4. Crime level ↔ Watch coverage
    # ------------------------------------------------------------------
    coverage = city.watch_coverage_pct
    if coverage < 50:
        # Each percent below 50% coverage contributes to rising crime
        crime_rise = (50.0 - coverage) / 50.0 * 0.3
        city.crime_level.apply(crime_rise, tick, cause="Reduced Watch coverage")
    elif coverage >= 80:
        # Strong Watch presence slowly suppresses unlicensed activity
        city.crime_level.apply(-0.1, tick, cause="Strong Watch presence")

    # ------------------------------------------------------------------
    # 5. Scandal escalation: ignored crises compound media pressure
    # ------------------------------------------------------------------
    # An unaddressed event that has been DETECTED for more than 24 hours without
    # any response triggers escalating coverage.  The longer the silence, the
    # worse the headlines.  Crucially this only fires for DETECTED (ignored)
    # events — a building in RESPONDING phase has an active response team and
    # citizens can see work underway, so the scandal does not escalate further.
    #
    # organisational_fragmentation.accelerates_trust_decay scales the damage:
    # at level 0.5 and factor 1.2, each scandal is 10% worse.
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

    for event in neglected:
        district = city.districts.get(event.target_district_id)
        if district:
            scandal_damage = -1.5 * district.media_attention_multiplier * scandal_org_frag_mult
            district.local_trust.apply(scandal_damage, tick, cause=f"{event.name} (scandal)")

    # ------------------------------------------------------------------
    # 7. Pending trust boosts: deferred gains from resilience_investment
    # ------------------------------------------------------------------
    for district in city.districts.values():
        due = [(t, amt, cause) for (t, amt, cause) in district.pending_trust_boosts if tick >= t]
        if due:
            district.pending_trust_boosts = [
                entry for entry in district.pending_trust_boosts if tick < entry[0]
            ]
            for _, amt, cause in due:
                district.local_trust.apply(amt, tick, cause=cause)

    # Press statement window: event is RESPONDING but only a statement was issued.
    # Scandal fires at half strength — citizens see the statement but no concrete action.
    # (slows_decay_multiplier: 0.5 from press_statement trust_effect)
    press_decay_mult = 0.5
    if cfg:
        ps_cfg = cfg.remedies.get("press_statement")
        if ps_cfg:
            press_decay_mult = ps_cfg.raw.get("trust_effect", {}).get("slows_decay_multiplier", 0.5)

    for event in city.visible_events:
        if event.phase != EventPhase.RESPONDING:
            continue
        if event.remedy_applied != "press_statement":
            continue
        if event.detected_tick is None:
            continue
        if tick - event.detected_tick < ticks_per_day:
            continue
        district = city.districts.get(event.target_district_id)
        if district:
            scandal_damage = -1.5 * district.media_attention_multiplier * scandal_org_frag_mult * press_decay_mult
            district.local_trust.apply(scandal_damage, tick, cause=f"{event.name} (muted scandal)")

    # ------------------------------------------------------------------
    # 6. Stressor drift: systemic conditions worsen through neglect
    # ------------------------------------------------------------------
    # neglect_increase: rises each day at least one event has been ignored for > 24h
    # budget_cut_increase: rises each month when public trust is below tax-penalty floor
    if cfg:
        trust_floor = 30  # mirrors tax-penalty threshold in apply_income()
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
            delta = effect.delta * district.media_attention_multiplier
            # Social inequality amplifies negative trust damage in vulnerable districts
            # and softens it in districts that benefit from the asymmetry.
            if delta < 0:
                delta *= _inequality_modifier(
                    district.stressors.get("social_inequality"),
                    city.stressors.get("social_inequality", 0.0),
                )
            district.local_trust.apply(delta, tick, cause=cause)
            return

    # Global metric
    metric = city.get_metric(effect.metric)
    if metric:
        metric.apply(effect.delta, tick, cause=cause)


# District social_inequality label → modifier applied to negative trust deltas only
_INEQUALITY_MODIFIERS: dict[str, callable] = {
    "victim":      lambda lvl: 1.0 + lvl * 0.8,            # Cockbill, Shades: +56% damage at level 0.7
    "moderate":    lambda lvl: 1.0 + lvl * 0.3,            # Small Gods: +21% at level 0.7
    "beneficiary": lambda lvl: max(0.3, 1.0 - lvl * 0.4),  # Nap Hill: 72% damage at level 0.7
}


def _inequality_modifier(label: str | None, global_level: float) -> float:
    """Return a trust-damage multiplier based on a district's inequality label and the city-wide level."""
    fn = _INEQUALITY_MODIFIERS.get(label)  # type: ignore[arg-type]
    return fn(global_level) if fn else 1.0