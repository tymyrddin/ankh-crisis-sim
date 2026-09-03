from __future__ import annotations

from dataclasses import dataclass, field

from src.models.building import Building
from src.models.metric import Metric


@dataclass
class District:
    id: str
    name: str
    description: str = ""

    wealth: float = 50.0
    density: float = 100.0
    infrastructure_quality: float = 1.0
    political_influence: float = 1.0
    media_attention_multiplier: float = 1.0
    wealth_archetype: str = "medium_wealth"
    is_residential: bool = True
    discovery_time_hours: tuple[float, float] = (24.0, 48.0)

    # district stressors are string labels, not levels
    stressors: dict[str, str] = field(default_factory=dict)

    local_trust: Metric = field(default_factory=lambda: Metric("local_trust", 50.0))
    buildings: dict[str, Building] = field(default_factory=dict)

    # (apply_at_tick, amount, cause); deferred gains and fading boosts, independent of any event
    scheduled_trust_changes: list[tuple[int, float, str]] = field(default_factory=list)

    @property
    def failure_probability_modifier(self) -> float:
        # infrastructure_quality is already the multiplier: 0.3 is safer, 3.0 is three times as likely
        return max(0.1, self.infrastructure_quality)

    @property
    def failed_building_count(self) -> int:
        return sum(1 for b in self.buildings.values() if b.is_failed)

    @property
    def degraded_building_count(self) -> int:
        return sum(1 for b in self.buildings.values() if b.is_degraded)

    @property
    def operational_building_count(self) -> int:
        return sum(1 for b in self.buildings.values() if b.is_operational)

    @property
    def failed_buildings(self) -> list[Building]:
        return [b for b in self.buildings.values() if b.is_failed]

    @property
    def active_event_count(self) -> int:
        return sum(1 for b in self.buildings.values() if b.active_event_id is not None)

    @property
    def is_in_crisis(self) -> bool:
        total = len(self.buildings)
        if total == 0:
            return False
        return self.failed_building_count > total / 2
