from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum


class BuildingStatus(StrEnum):
    OPERATIONAL = "operational"
    DEGRADED = "degraded"
    FAILED = "failed"


@dataclass
class DependencyStrengths:
    critical: list[str] = field(default_factory=list)
    operational: list[str] = field(default_factory=list)
    strategic: list[str] = field(default_factory=list)


@dataclass
class Building:
    id: str
    name: str
    type_id: str
    district_id: str
    position: tuple[int, int]
    status: BuildingStatus = BuildingStatus.OPERATIONAL
    dependencies: DependencyStrengths = field(default_factory=DependencyStrengths)

    # Populated from building type config at load time; the instance may override the modifier
    detection_time_modifier: float = 1.0
    sensitivity: str = "medium"
    consumes: list[str] = field(default_factory=list)
    produces: list[str] = field(default_factory=list)

    hidden_failure: bool = False
    failure_tick: int | None = None
    active_event_id: str | None = None
    recurrence_risk: float = 0.0

    @property
    def is_failed(self) -> bool:
        return self.status == BuildingStatus.FAILED

    @property
    def is_degraded(self) -> bool:
        return self.status == BuildingStatus.DEGRADED

    @property
    def is_operational(self) -> bool:
        return self.status == BuildingStatus.OPERATIONAL

    def fail(self, tick: int, event_id: str) -> None:
        self.status = BuildingStatus.FAILED
        self.failure_tick = tick
        self.active_event_id = event_id

    def restore(self, recurrence_risk: float = 0.0) -> None:
        self.status = BuildingStatus.OPERATIONAL
        self.failure_tick = None
        self.active_event_id = None
        self.hidden_failure = False
        self.recurrence_risk = recurrence_risk
