"""District model: a named area of the city with local metrics and buildings."""

from __future__ import annotations

from dataclasses import dataclass, field

from src.models.building import Building
from src.models.metric import Metric


@dataclass
class District:
    id: str
    name: str
    description: str = ""

    # Static properties (from YAML)
    wealth: float = 50.0
    density: float = 100.0
    infrastructure_quality: float = 1.0
    political_influence: float = 1.0
    media_attention_multiplier: float = 1.0
    wealth_archetype: str = "medium_wealth"
    is_residential: bool = True
    discovery_time_hours: tuple[float, float] = (24.0, 48.0)
    protest_threshold: float = 20.0
    narrative_hooks: list[str] = field(default_factory=list)

    # Stressor levels (mutable, evolve over game)
    stressors: dict[str, float] = field(default_factory=dict)

    # Runtime state
    local_trust: Metric = field(default_factory=lambda: Metric("local_trust", 50.0))
    buildings: dict[str, Building] = field(default_factory=dict)

    # Pending delayed trust boosts: (apply_at_tick, amount, cause)
    # Populated by _resolve_event() for remedies with trust_effect.delayed_days.
    pending_trust_boosts: list[tuple[int, float, str]] = field(default_factory=list)

    @property
    def failure_probability_modifier(self) -> float:
        """The value IS the modifier: 0.3 = 70% less likely, 3.0 = 3x more likely."""
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
        """List of currently failed buildings in this district."""
        return [b for b in self.buildings.values() if b.is_failed]

    @property
    def active_event_count(self) -> int:
        """Number of buildings currently carrying an active event."""
        return sum(1 for b in self.buildings.values() if b.active_event_id is not None)

    @property
    def is_in_crisis(self) -> bool:
        """A district is in crisis if more than half its buildings have failed."""
        total = len(self.buildings)
        if total == 0:
            return False
        return self.failed_building_count > total / 2