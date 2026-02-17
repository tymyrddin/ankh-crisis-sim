"""End condition evaluation — checks for loss, completion, or escape each tick."""

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
    """Check all end conditions. Returns the first one triggered, or None."""
    for condition in cfg.end_conditions:
        result = _check_condition(condition, city, elapsed_days)
        if result:
            return result
    return None


def _check_condition(
    condition: EndCondition,
    city: City,
    elapsed_days: int,
) -> EndResult | None:
    trigger = condition.trigger

    if not isinstance(trigger, dict):
        return None  # player_action triggers are handled elsewhere

    # Metric threshold check
    if "metric" in trigger:
        metric = city.get_metric(trigger["metric"])
        if not metric:
            return None

        if "below" in trigger:
            threshold = trigger["below"]
            sustained = trigger.get("sustained_days", 0)

            if metric.value < threshold:
                # Check if it's been sustained long enough
                if sustained > 0:
                    # Look at history to see how long below threshold
                    days_below = _days_below_threshold(metric, threshold)
                    if days_below < sustained:
                        return None

                return EndResult(
                    triggered=True,
                    condition_id=condition.id,
                    label=condition.label,
                    narrative=condition.narrative,
                )

    # Days elapsed check (term completion)
    if "days_elapsed" in trigger:
        if elapsed_days >= trigger["days_elapsed"]:
            return EndResult(
                triggered=True,
                condition_id=condition.id,
                label=condition.label,
                narrative=condition.narrative,
            )

    # Districts in crisis check
    if "districts_in_crisis" in trigger:
        if city.districts_in_crisis >= trigger["districts_in_crisis"]:
            return EndResult(
                triggered=True,
                condition_id=condition.id,
                label=condition.label,
                narrative=condition.narrative,
            )

    return None


def _days_below_threshold(metric, threshold: float) -> int:
    """Count consecutive days the metric has been below threshold."""
    if not metric.history:
        return 0

    consecutive_ticks = 0
    for snapshot in reversed(metric.history):
        if snapshot.value < threshold:
            consecutive_ticks += 1
        else:
            break

    return consecutive_ticks // 24  # approximate: ticks to days