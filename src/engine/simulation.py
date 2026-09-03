from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from src.config.loader import GameConfig, build_city
from src.engine.clock import GameClock
from src.engine.dependencies import propagate_cascades
from src.engine.detection import process_detection
from src.engine.end_check import EndResult, check_end_conditions
from src.engine.events import generate_events
from src.engine.metrics import (
    apply_delayed_effects,
    apply_duration_penalties,
    apply_immediate_effects,
    apply_income,
    apply_passive_dynamics,
    update_global_trust_from_districts,
)
from src.engine.narrative import generate_headline, generate_story
from src.engine.remedies import RemedyResult, apply_remedy, process_remedy_completions
from src.models.city import City
from src.models.event import GameEvent


@dataclass
class TickResult:
    tick: int = 0
    new_events: list[GameEvent] = field(default_factory=list)
    detected_events: list[GameEvent] = field(default_factory=list)
    cascade_events: list[GameEvent] = field(default_factory=list)
    headlines: list[str] = field(default_factory=list)
    completed_remedies: list[str] = field(default_factory=list)
    completed_remedy_events: list[GameEvent] = field(default_factory=list)
    end_result: EndResult | None = None


class Simulation:
    def __init__(self, config_dir: str | Path = "config"):
        self.config_dir = Path(config_dir)
        self.cfg: GameConfig | None = None
        self.city: City | None = None
        self.clock = GameClock()
        self._initialised = False

    def initialise(self) -> None:
        self.cfg, self.city = build_city(self.config_dir)
        self.clock = GameClock(
            ticks_per_day=self.cfg.time.ticks_per_day,
            starting_day=self.cfg.time.starting_day,
            starting_hour=self.cfg.time.starting_hour,
            speed_multiplier=self.cfg.speed.default_multiplier,
        )
        self._initialised = True

    def tick(self) -> TickResult:
        assert self._initialised and self.cfg and self.city

        result = TickResult()
        self.clock.advance()
        result.tick = self.clock.tick

        new_events = generate_events(self.cfg, self.city, self.clock.tick)
        for event in new_events:
            self.city.events.append(event)
        result.new_events = new_events

        detected = process_detection(self.cfg, self.city, self.clock.tick)
        result.detected_events = detected

        for event in detected:
            apply_immediate_effects(self.city, event, self.clock.tick)
            if not event.headline:
                event.headline = generate_headline(self.cfg, self.city, event)
            if not event.story:
                event.story = generate_story(self.cfg, self.city, event, self.clock.tick)
            if event.headline:
                result.headlines.append(event.headline)

        # per-domain cascade amplifiers from stressors with amplifies_cascade
        domain_multipliers: dict[str, float] = {}
        for stressor_id, sc in self.cfg.stressors.items():
            level = self.city.stressors.get(stressor_id, 0.0)
            for effect in sc.raw.get("effects", []):
                for domain in effect.get("amplifies_cascade", []):
                    domain_multipliers[domain] = domain_multipliers.get(domain, 1.0) * (1.0 + level * 0.5)

        cascades = propagate_cascades(
            self.city, self.clock.tick,
            self.cfg.time.ticks_per_day,
            self.cfg.settings.cascade_multiplier,
            domain_multipliers,
        )
        for ce in cascades:
            self.city.events.append(ce)
            if not ce.story:
                ce.story = generate_story(self.cfg, self.city, ce, self.clock.tick)
            if ce.headline:
                result.headlines.append(ce.headline)
        result.cascade_events = cascades

        apply_delayed_effects(self.city, self.clock.tick)

        apply_duration_penalties(self.city, self.clock.tick, self.cfg.time.ticks_per_day)

        completed = process_remedy_completions(self.cfg, self.city, self.clock.tick)
        result.completed_remedies = [msg for msg, _ in completed]
        result.completed_remedy_events = [evt for _, evt in completed]

        apply_income(self.city, self.cfg, self.clock.tick, self.cfg.time.ticks_per_day)

        update_global_trust_from_districts(self.city, self.clock.tick)

        apply_passive_dynamics(self.city, self.clock.tick, self.cfg.time.ticks_per_day, self.cfg)

        result.end_result = check_end_conditions(
            self.cfg, self.city, self.clock.elapsed_days
        )

        return result

    def pause(self) -> None:
        self.clock.pause()

    def resume(self) -> None:
        self.clock.resume()

    def set_speed(self, multiplier: float) -> None:
        self.clock.set_speed(multiplier)

    def apply_remedy(self, event_id: str, remedy_id: str) -> RemedyResult:
        assert self.cfg and self.city
        event = next((e for e in self.city.active_events if e.id == event_id), None)
        if not event:
            return RemedyResult(success=False, message=f"Event {event_id} not found or not active")
        return apply_remedy(self.cfg, self.city, event, remedy_id, self.clock.tick)

    def emergency_borrow(self, lender_id: str) -> RemedyResult:
        """lender_id is a key under budget.emergency_borrowing in game.yml."""
        assert self.cfg and self.city
        lenders = self.cfg.budget_raw.get("emergency_borrowing", {})
        lender = lenders.get(lender_id)
        if not lender:
            return RemedyResult(success=False, message=f"Unknown lender: {lender_id}")
        if not lender.get("available", False):
            return RemedyResult(success=False, message="This lender is not currently available")
        amount = float(lender.get("max_amount", 1000))
        label = lender.get("label", lender_id)
        self.city.budget.apply(amount, self.clock.tick, cause=f"Emergency loan: {label}")

        reg_cost = float(lender.get("regulatory_pressure_cost", 0))
        if reg_cost:
            self.city.regulatory_pressure.apply(reg_cost, self.clock.tick, cause=f"Emergency loan: {label}")

        stability_cost = float(lender.get("stability_cost", 0))
        if stability_cost:
            self.city.political_stability.apply(-stability_cost, self.clock.tick, cause=f"Emergency loan: {label}")

        costs = []
        if reg_cost:
            costs.append(f"regulatory pressure +{reg_cost:.0f}")
        if stability_cost:
            costs.append(f"stability −{stability_cost:.0f}")
        cost_str = "; ".join(costs) if costs else "no immediate political cost"
        return RemedyResult(
            success=True,
            message=f"Emergency loan of {amount:.0f} AM$ secured from {label} ({cost_str})",
            cost=-amount,
        )

    def resign(self) -> EndResult:
        assert self.cfg
        for cond in self.cfg.end_conditions:
            if cond.id == "resignation":
                return EndResult(
                    triggered=True,
                    condition_id=cond.id,
                    label=cond.label,
                    narrative=cond.narrative,
                )
        return EndResult(triggered=False)

    def retire(self) -> EndResult:
        assert self.cfg and self.city
        for cond in self.cfg.end_conditions:
            if cond.id != "early_retirement":
                continue
            if cond.min_days and self.clock.elapsed_days < cond.min_days:
                return EndResult(
                    triggered=False,
                    condition_id=cond.id,
                    label=cond.label,
                    narrative=f"Retirement requires at least {cond.min_days} days served.",
                )
            return EndResult(
                triggered=True,
                condition_id=cond.id,
                label=cond.label,
                narrative=cond.narrative,
            )
        return EndResult(triggered=False)

    def get_visible_events(self) -> list[GameEvent]:
        return self.city.visible_events if self.city else []

    def get_state(self) -> City:
        assert self.city
        return self.city