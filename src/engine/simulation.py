"""Main simulation loop — orchestrates all engine subsystems per tick."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from src.config.loader import GameConfig, build_city
from src.engine.clock import ClockState, GameClock
from src.engine.dependencies import propagate_cascades
from src.engine.detection import process_detection
from src.engine.end_check import EndResult, check_end_conditions
from src.engine.events import generate_events
from src.engine.metrics import (
    apply_delayed_effects,
    apply_duration_penalties,
    apply_immediate_effects,
    apply_income,
    update_global_trust_from_districts,
)
from src.engine.narrative import generate_headline
from src.engine.remedies import RemedyResult, apply_remedy, process_remedy_completions
from src.models.city import City
from src.models.event import GameEvent


@dataclass
class TickResult:
    """What happened during a single tick."""
    tick: int = 0
    new_events: list[GameEvent] = field(default_factory=list)
    detected_events: list[GameEvent] = field(default_factory=list)
    cascade_events: list[GameEvent] = field(default_factory=list)
    headlines: list[str] = field(default_factory=list)
    completed_remedies: list[str] = field(default_factory=list)
    end_result: EndResult | None = None


class Simulation:
    """The main simulation controller. GUI calls into this."""

    def __init__(self, config_dir: str | Path = "config"):
        self.config_dir = Path(config_dir)
        self.cfg: GameConfig | None = None
        self.city: City | None = None
        self.clock = GameClock()
        self._initialised = False

    def initialise(self) -> None:
        """Load config and build initial city state."""
        self.cfg, self.city = build_city(self.config_dir)
        self.clock = GameClock(
            ticks_per_day=self.cfg.time.ticks_per_day,
            starting_day=self.cfg.time.starting_day,
            starting_hour=self.cfg.time.starting_hour,
            speed_multiplier=self.cfg.speed.default_multiplier,
        )
        self._initialised = True

    def tick(self) -> TickResult:
        """Advance the simulation by one tick. Returns what happened."""
        assert self._initialised and self.cfg and self.city

        result = TickResult()
        self.clock.advance()
        result.tick = self.clock.tick

        # 1. Generate new events
        new_events = generate_events(self.cfg, self.city, self.clock.tick)
        for event in new_events:
            self.city.events.append(event)
        result.new_events = new_events

        # 2. Detection — reveal hidden failures
        detected = process_detection(self.cfg, self.city, self.clock.tick)
        result.detected_events = detected

        # 3. Apply immediate effects for newly detected events
        for event in detected:
            apply_immediate_effects(self.city, event, self.clock.tick)
            headline = generate_headline(self.cfg, self.city, event)
            if headline:
                event.headline = headline
                result.headlines.append(headline)

        # 4. Cascade propagation
        cascades = propagate_cascades(self.city, self.clock.tick)
        for ce in cascades:
            self.city.events.append(ce)
            if ce.headline:
                result.headlines.append(ce.headline)
        result.cascade_events = cascades

        # 5. Delayed effects
        apply_delayed_effects(self.city, self.clock.tick)

        # 6. Duration penalties
        apply_duration_penalties(self.city, self.clock.tick, self.cfg.time.ticks_per_day)

        # 7. Remedy completions
        completed = process_remedy_completions(self.cfg, self.city, self.clock.tick)
        result.completed_remedies = completed

        # 8. Income
        apply_income(self.city, self.cfg, self.clock.tick, self.cfg.time.ticks_per_day)

        # 9. Update global trust from district averages
        update_global_trust_from_districts(self.city, self.clock.tick)

        # 10. End condition check
        result.end_result = check_end_conditions(
            self.cfg, self.city, self.clock.elapsed_days
        )

        return result

    # --- Player actions ---

    def pause(self) -> None:
        self.clock.pause()

    def resume(self) -> None:
        self.clock.resume()

    def set_speed(self, multiplier: float) -> None:
        self.clock.set_speed(multiplier)

    def apply_remedy(self, event_id: str, remedy_id: str) -> RemedyResult:
        """Player applies a remedy to an event."""
        assert self.cfg and self.city
        event = next((e for e in self.city.active_events if e.id == event_id), None)
        if not event:
            return RemedyResult(success=False, message=f"Event {event_id} not found or not active")
        return apply_remedy(self.cfg, self.city, event, remedy_id, self.clock.tick)

    def get_visible_events(self) -> list[GameEvent]:
        """Get all events the player can currently see."""
        return self.city.visible_events if self.city else []

    def get_state(self) -> City:
        """Return current city state for GUI rendering."""
        assert self.city
        return self.city