"""City model: the top-level container holding all districts, global metrics, and active events."""

from __future__ import annotations

from dataclasses import dataclass, field

from src.models.district import District
from src.models.event import GameEvent
from src.models.metric import Metric


@dataclass
class City:
    districts: dict[str, District] = field(default_factory=dict)
    events: list[GameEvent] = field(default_factory=list)

    # Global metrics
    public_trust: Metric = field(default_factory=lambda: Metric("public_trust", 68.0))
    budget: Metric = field(default_factory=lambda: Metric("budget", 4200.0, min_value=0, max_value=99999))
    regulatory_pressure: Metric = field(default_factory=lambda: Metric("regulatory_pressure", 18.0))
    political_stability: Metric = field(default_factory=lambda: Metric("political_stability", 75.0))
    legitimacy: Metric = field(default_factory=lambda: Metric("legitimacy", 82.0))
    public_health: Metric = field(default_factory=lambda: Metric("public_health", 75.0))
    crime_level: Metric = field(default_factory=lambda: Metric("crime_level", 22.0))

    # Stressor levels (city-wide, evolve over game)
    stressors: dict[str, float] = field(default_factory=dict)

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
    def total_failed_buildings(self) -> int:
        """Total failed buildings across all districts."""
        return sum(d.failed_building_count for d in self.districts.values())

    @property
    def events_by_domain(self) -> dict[str, list[GameEvent]]:
        """Visible active events grouped by infrastructure domain."""
        result: dict[str, list[GameEvent]] = {}
        for event in self.visible_events:
            result.setdefault(event.domain, []).append(event)
        return result

    @property
    def infrastructure_health_pct(self) -> float:
        """Percentage of buildings across all districts that are operational."""
        total = sum(len(d.buildings) for d in self.districts.values())
        if total == 0:
            return 100.0
        operational = sum(d.operational_building_count for d in self.districts.values())
        return (operational / total) * 100.0

    @property
    def watch_coverage_pct(self) -> float:
        """Percentage of security buildings that are currently operational."""
        security = [
            b for d in self.districts.values()
            for b in d.buildings.values()
            if b.type_id == "security"
        ]
        if not security:
            return 100.0
        return sum(1 for b in security if b.is_operational) / len(security) * 100.0

    def get_building(self, building_id: str):
        """Find a building across all districts."""
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
        """Shaped 0-1 view of the linear narrative_effects counter (tanh)."""
        from src.engine.metrics import narrative_effects_shaped
        raw = self.stressors.get("narrative_effects", 0.0)
        return narrative_effects_shaped(raw, "tanh")