from __future__ import annotations

from dataclasses import dataclass

from src.config.loader import EndCondition, GameConfig
from src.models.city import City


@dataclass
class EndResult:
    triggered: bool
    condition_id: str = ""
    label: str = ""
    narrative: str = ""


def check_end_conditions(
    cfg: GameConfig,
    city: City,
    elapsed_days: int,
) -> EndResult | None:
    for condition in cfg.end_conditions:
        result = _check_condition(condition, city, elapsed_days, cfg)
        if result:
            return result
    return None


def _check_condition(
    condition: EndCondition,
    city: City,
    elapsed_days: int,
    cfg: GameConfig,
) -> EndResult | None:
    trigger = condition.trigger

    if not isinstance(trigger, dict):
        # player_action triggers go through Simulation.resign() and retire()
        return None

    if "metric" in trigger:
        metric = city.get_metric(trigger["metric"])
        if not metric:
            return None

        if "below" in trigger:
            threshold = trigger["below"]
            sustained = trigger.get("sustained_days", 0)

            if metric.value < threshold:
                if sustained > 0:
                    days_below = _days_below_threshold(
                        metric, threshold, elapsed_days, cfg.time.ticks_per_day
                    )
                    if days_below < sustained:
                        return None

                return EndResult(
                    triggered=True,
                    condition_id=condition.id,
                    label=condition.label,
                    narrative=condition.narrative,
                )

    if "days_elapsed" in trigger:
        target_days = (
            cfg.settings.game_duration_days
            if cfg.settings.game_duration_days > 0
            else trigger["days_elapsed"]
        )
        if elapsed_days >= target_days:
            return EndResult(
                triggered=True,
                condition_id=condition.id,
                label=condition.label,
                narrative=condition.narrative,
            )

    if "districts_in_crisis" in trigger:
        if city.districts_in_crisis >= trigger["districts_in_crisis"]:
            return EndResult(
                triggered=True,
                condition_id=condition.id,
                label=condition.label,
                narrative=condition.narrative,
            )

    return None


def _days_below_threshold(
    metric,
    threshold: float,
    elapsed_days: int,
    ticks_per_day: int,
) -> int:
    # Snapshots only land when a metric changes, so count from the tick of the
    # first snapshot in the current run rather than the number of snapshots.
    first_below_tick: int | None = None
    for snapshot in reversed(metric.history):
        if snapshot.value < threshold:
            first_below_tick = snapshot.tick
        else:
            break
    if first_below_tick is None:
        return 0
    return elapsed_days - first_below_tick // ticks_per_day