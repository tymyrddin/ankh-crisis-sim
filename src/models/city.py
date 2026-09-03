from __future__ import annotations

from dataclasses import dataclass, field

from src.models.building import Building
from src.models.district import District
from src.models.event import GameEvent
from src.models.metric import Metric


@dataclass
class City:
    districts: dict[str, District] = field(default_factory=dict)
    events: list[GameEvent] = field(default_factory=list)

    # starting values and bounds come from config; these are placeholders until the loader fills them
    public_trust: Metric = field(default_factory=lambda: Metric("public_trust", 0.0))
    budget: Metric = field(default_factory=lambda: Metric("budget", 0.0))
    regulatory_pressure: Metric = field(default_factory=lambda: Metric("regulatory_pressure", 0.0))
    political_stability: Metric = field(default_factory=lambda: Metric("political_stability", 0.0))
    legitimacy: Metric = field(default_factory=lambda: Metric("legitimacy", 0.0))
    public_health: Metric = field(default_factory=lambda: Metric("public_health", 0.0))
    crime_level: Metric = field(default_factory=lambda: Metric("crime_level", 0.0))

    # city-wide levels, 0 to 1, drift over the game
    stressors: dict[str, float] = field(default_factory=dict)
    # unbounded counter of press statements, contradictions and scandals; shaped for display
    narrative_effects: float = 0.0

    @property
    def active_events(self) -> list[GameEvent]:
        return [e for e in self.events if e.is_active]

    @property
    def visible_events(self) -> list[GameEvent]:
        return [e for e in self.events if e.is_visible and e.is_active]

    @property
    def districts_in_crisis(self) -> int:
        return sum(1 for d in self.districts.values() if d.is_in_crisis)

    @property
    def infrastructure_health_pct(self) -> float:
        total = sum(len(d.buildings) for d in self.districts.values())
        if total == 0:
            return 100.0
        operational = sum(d.operational_building_count for d in self.districts.values())
        return (operational / total) * 100.0

    @property
    def watch_coverage_pct(self) -> float:
        security = [
            b for d in self.districts.values()
            for b in d.buildings.values()
            if b.type_id == "security"
        ]
        if not security:
            return 100.0
        return sum(1 for b in security if b.is_operational) / len(security) * 100.0

    def get_building(self, building_id: str) -> Building | None:
        for district in self.districts.values():
            if building_id in district.buildings:
                return district.buildings[building_id]
        return None

    def get_district_for_building(self, building_id: str) -> District | None:
        for district in self.districts.values():
            if building_id in district.buildings:
                return district
        return None

    def get_metric(self, name: str) -> Metric | None:
        return getattr(self, name, None)

    @property
    def narrative_effects_display(self) -> float:
        from src.engine.metrics import narrative_effects_shaped  # avoids a models -> engine import cycle
        return narrative_effects_shaped(self.narrative_effects, "tanh")
