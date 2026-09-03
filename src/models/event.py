from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum


class EventPhase(StrEnum):
    HIDDEN = "hidden"
    DETECTED = "detected"
    RESPONDING = "responding"
    RESOLVED = "resolved"  # the building may fail again


@dataclass
class MetricEffect:
    metric: str
    delta: float
    scope: str = "global"  # or "district"
    district_id: str | None = None


@dataclass
class DelayedEffect:
    delay_hours: int
    effects: list[MetricEffect]
    applied: bool = False


@dataclass
class GameEvent:
    id: str
    template_id: str
    name: str
    category: str
    domain: str
    phase: EventPhase = EventPhase.HIDDEN
    target_district_id: str = ""
    target_building_id: str = ""
    created_tick: int = 0
    detected_tick: int | None = None
    resolved_tick: int | None = None

    immediate_effects: list[MetricEffect] = field(default_factory=list)
    delayed_effects: list[DelayedEffect] = field(default_factory=list)
    duration_penalty_per_day: float = 0.0
    duration_penalty_metric: str = "local_trust"

    cascade_dependency: str | None = None
    cascade_scope: str = "neighbours"  # anything else means the whole city

    discovery_time_hours: float | None = None

    headline: str = ""
    story: str = ""

    remedy_applied: str | None = None
    remedy_applied_tick: int | None = None
    # a press statement does not occupy the response slot; it runs alongside DETECTED
    statement_remedy: str | None = None
    statement_tick: int | None = None
    # hours, fixed when the remedy is applied; the completion check reads this
    effective_downtime_hours: float | None = None

    # raised by do_nothing
    cascade_risk_boost: float = 1.0

    # an impact tag, not a domain; residential events keep their utility domain
    residential_impact: bool = False

    @property
    def is_active(self) -> bool:
        return self.phase in (EventPhase.HIDDEN, EventPhase.DETECTED, EventPhase.RESPONDING)

    @property
    def is_visible(self) -> bool:
        return self.phase != EventPhase.HIDDEN

    def detect(self, tick: int) -> None:
        if self.phase == EventPhase.HIDDEN:
            self.phase = EventPhase.DETECTED
            self.detected_tick = tick

    def start_response(self, remedy: str, tick: int) -> None:
        self.phase = EventPhase.RESPONDING
        self.remedy_applied = remedy
        self.remedy_applied_tick = tick

    def resolve(self, tick: int) -> None:
        self.phase = EventPhase.RESOLVED
        self.resolved_tick = tick
