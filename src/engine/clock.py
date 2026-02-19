"""Game clock: manages simulated time with pause and speed control."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class ClockState(str, Enum):
    PAUSED = "paused"
    RUNNING = "running"


@dataclass
class GameClock:
    tick: int = 0
    ticks_per_day: int = 24
    starting_day: int = 1
    starting_hour: int = 8
    speed_multiplier: float = 1.0
    state: ClockState = ClockState.PAUSED

    def advance(self) -> int:
        """Advance one tick. Returns the new tick number."""
        self.tick += 1
        return self.tick

    @property
    def day(self) -> int:
        return self.starting_day + self.tick // self.ticks_per_day

    @property
    def hour(self) -> int:
        return (self.starting_hour + self.tick) % self.ticks_per_day

    @property
    def time_string(self) -> str:
        return f"Day {self.day} - {self.hour:02d}:00"

    @property
    def elapsed_days(self) -> int:
        return self.tick // self.ticks_per_day

    def hours_since(self, past_tick: int) -> int:
        return self.tick - past_tick

    def pause(self) -> None:
        self.state = ClockState.PAUSED

    def resume(self) -> None:
        self.state = ClockState.RUNNING

    def set_speed(self, multiplier: float) -> None:
        self.speed_multiplier = max(0.1, multiplier)

    @property
    def is_running(self) -> bool:
        return self.state == ClockState.RUNNING