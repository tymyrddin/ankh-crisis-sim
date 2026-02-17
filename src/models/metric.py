"""Metric value with history tracking for post-game timeline."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class MetricSnapshot:
    tick: int
    value: float
    cause: str = ""


@dataclass
class Metric:
    name: str
    value: float
    min_value: float = 0.0
    max_value: float = 100.0
    history: list[MetricSnapshot] = field(default_factory=list)

    def apply(self, delta: float, tick: int, cause: str = "") -> float:
        """Apply a change, clamp, record history, return new value."""
        old = self.value
        self.value = max(self.min_value, min(self.max_value, self.value + delta))
        if self.value != old:
            self.history.append(MetricSnapshot(tick=tick, value=self.value, cause=cause))
        return self.value

    def set(self, value: float, tick: int, cause: str = "") -> None:
        self.value = max(self.min_value, min(self.max_value, value))
        self.history.append(MetricSnapshot(tick=tick, value=self.value, cause=cause))

    @property
    def is_critical(self) -> bool:
        return self.value <= self.min_value + (self.max_value - self.min_value) * 0.1