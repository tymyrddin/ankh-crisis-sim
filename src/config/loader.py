"""YAML config loader — reads all config files and assembles a City + game settings."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

import yaml

from src.models.building import Building, BuildingStatus, DependencyStrengths
from src.models.city import City
from src.models.district import District
from src.models.event import DelayedEffect, MetricEffect
from src.models.metric import Metric


def _load_yaml(path: Path) -> dict | list:
    with open(path) as f:
        return yaml.safe_load(f)


# ---------------------------------------------------------------------------
# Config data classes (read-only reference data, not runtime state)
# ---------------------------------------------------------------------------

@dataclass
class TimeConfig:
    tick_hours: int = 1
    ticks_per_day: int = 24
    term_length_days: int = 1460
    starting_day: int = 1
    starting_hour: int = 8


@dataclass
class SpeedConfig:
    seconds_per_game_hour: float = 1.0
    default_multiplier: float = 1.0
    fast_multiplier: float = 10.0
    max_multiplier: float = 50.0


@dataclass
class RemedyConfig:
    id: str
    label: str
    description: str = ""
    base_cost: int = 0
    downtime_hours: int = 0
    recurrence_risk: float = 0.0
    infrastructure_quality_boost: float = 0.0
    raw: dict = field(default_factory=dict)


@dataclass
class EventTemplate:
    id: str
    name: str
    category: str
    domain: str = ""
    target_building_types: list[str] = field(default_factory=list)
    target_districts: list[str] = field(default_factory=list)
    target_buildings: list[str] = field(default_factory=list)
    probability_base: float = 0.001
    stressor_amplifiers: dict[str, float] = field(default_factory=dict)
    headlines: list[str] = field(default_factory=list)
    stories: list[str] = field(default_factory=list)
    raw: dict = field(default_factory=dict)

    # Pre-parsed effects
    immediate_effects: list[MetricEffect] = field(default_factory=list)
    delayed_effects: list[DelayedEffect] = field(default_factory=list)
    duration_penalty_per_day: float = 0.0
    duration_penalty_metric: str = "local_trust"
    cascade_dependency: str | None = None
    cascade_scope: str = "neighbours"


@dataclass
class StressorConfig:
    id: str
    label: str
    description: str = ""
    starting_level: float = 0.5
    raw: dict = field(default_factory=dict)


@dataclass
class BuildingTypeConfig:
    id: str
    label: str
    sensitivity: str = "medium"
    detection_time_modifier: float = 1.0
    consumes: list[str] = field(default_factory=list)
    produces: list[str] = field(default_factory=list)
    dependency_strengths: dict[str, list[str]] = field(default_factory=dict)


@dataclass
class EndCondition:
    id: str
    label: str
    description: str = ""
    narrative: str = ""
    trigger: dict = field(default_factory=dict)


@dataclass
class GameConfig:
    """All loaded configuration for a game session."""
    time: TimeConfig = field(default_factory=TimeConfig)
    speed: SpeedConfig = field(default_factory=SpeedConfig)
    active_districts: list[str] = field(default_factory=list)
    remedies: dict[str, RemedyConfig] = field(default_factory=dict)
    event_templates: list[EventTemplate] = field(default_factory=list)
    stressors: dict[str, StressorConfig] = field(default_factory=dict)
    building_types: dict[str, BuildingTypeConfig] = field(default_factory=dict)
    end_conditions: list[EndCondition] = field(default_factory=list)
    detection_raw: dict = field(default_factory=dict)
    metrics_global_raw: dict = field(default_factory=dict)
    metrics_district_raw: dict = field(default_factory=dict)
    headlines_raw: dict = field(default_factory=dict)
    stories_raw: dict = field(default_factory=dict)
    starting_values: dict[str, float] = field(default_factory=dict)
    budget_income: dict = field(default_factory=dict)


# ---------------------------------------------------------------------------
# Parsing helpers
# ---------------------------------------------------------------------------

def _parse_metric_effects(effects_list: list[dict]) -> list[MetricEffect]:
    result = []
    for e in effects_list:
        result.append(MetricEffect(
            metric=e["metric"],
            delta=e["delta"],
            scope=e.get("scope", "global"),
            district_id=e.get("district_id"),
        ))
    return result


def _parse_event_template(raw: dict) -> EventTemplate:
    tmpl = EventTemplate(
        id=raw["id"],
        name=raw["name"],
        category=raw["category"],
        domain=raw.get("domain", ""),
        target_building_types=raw.get("target_building_types", []),
        target_districts=raw.get("target_districts", []),
        target_buildings=raw.get("target_buildings", []),
        probability_base=raw.get("probability_base", 0.001),
        stressor_amplifiers=raw.get("stressor_amplifiers", {}),
        headlines=raw.get("headlines", []),
        stories=raw.get("stories", []),
        raw=raw,
    )

    impact = raw.get("impact", {})
    if "immediate" in impact:
        tmpl.immediate_effects = _parse_metric_effects(impact["immediate"])
    if "secondary" in impact:
        sec = impact["secondary"]
        tmpl.delayed_effects = [DelayedEffect(
            delay_hours=sec.get("delay_hours", 24),
            effects=_parse_metric_effects(sec.get("effects", [])),
        )]
    if "duration_penalty" in impact:
        dp = impact["duration_penalty"]
        tmpl.duration_penalty_per_day = dp.get("per_day_unresolved", 0)
        tmpl.duration_penalty_metric = dp.get("metric", "local_trust")

    cascade = raw.get("cascade", {})
    if cascade:
        tmpl.cascade_dependency = cascade.get("dependency")
        tmpl.cascade_scope = cascade.get("propagate_to", "neighbours")

    return tmpl


def _parse_building_instance(raw: dict) -> Building:
    deps_raw = raw.get("dependencies", {})
    deps = DependencyStrengths(
        critical=deps_raw.get("critical", []),
        operational=deps_raw.get("operational", []),
        strategic=deps_raw.get("strategic", []),
    )
    status_str = raw.get("status", "operational")
    return Building(
        id=raw["id"],
        name=raw["name"],
        type_id=raw["type"],
        district_id=raw["district"],
        position=tuple(raw.get("position", [0, 0])),
        status=BuildingStatus(status_str),
        dependencies=deps,
        narrative_hooks=raw.get("narrative_hooks", []),
        detection_time_modifier_override=raw.get("detection_time_modifier_override"),
    )


# ---------------------------------------------------------------------------
# Main loader
# ---------------------------------------------------------------------------

def load_config(config_dir: str | Path) -> GameConfig:
    """Load all YAML files from the config directory and return a GameConfig."""
    config_dir = Path(config_dir)
    cfg = GameConfig()

    # --- game.yml ---
    game_raw = _load_yaml(config_dir / "game.yml")
    time_raw = game_raw.get("time", {})
    cfg.time = TimeConfig(
        tick_hours=time_raw.get("tick_hours", 1),
        ticks_per_day=time_raw.get("ticks_per_day", 24),
        term_length_days=time_raw.get("term_length_days", 1460),
        starting_day=time_raw.get("starting_day", 1),
        starting_hour=time_raw.get("starting_hour", 8),
    )
    speed_raw = game_raw.get("speed", {})
    cfg.speed = SpeedConfig(
        seconds_per_game_hour=speed_raw.get("seconds_per_game_hour", 1.0),
        default_multiplier=speed_raw.get("default_multiplier", 1.0),
        fast_multiplier=speed_raw.get("fast_multiplier", 10.0),
        max_multiplier=speed_raw.get("max_multiplier", 50.0),
    )
    cfg.active_districts = game_raw.get("active_districts", [])
    cfg.starting_values = game_raw.get("starting_values", {})
    cfg.budget_income = game_raw.get("budget", {}).get("income_per_month", {})

    # --- metrics ---
    cfg.metrics_global_raw = _load_yaml(config_dir / "metrics" / "global.yml")
    cfg.metrics_district_raw = _load_yaml(config_dir / "metrics" / "district.yml")

    # --- building types ---
    types_raw = _load_yaml(config_dir / "buildings" / "_types.yml")
    for type_id, tdata in types_raw.items():
        dep_str = tdata.get("dependency_strengths", {})
        cfg.building_types[type_id] = BuildingTypeConfig(
            id=type_id,
            label=tdata.get("label", type_id),
            sensitivity=tdata.get("sensitivity", "medium"),
            detection_time_modifier=tdata.get("detection_time_modifier", 1.0),
            consumes=tdata.get("consumes", []),
            produces=tdata.get("produces", []),
            dependency_strengths=dep_str,
        )

    # --- threats ---
    cfg.stressors = {}
    stressors_raw = _load_yaml(config_dir / "threats" / "stressors.yml")
    for sid, sdata in stressors_raw.items():
        cfg.stressors[sid] = StressorConfig(
            id=sid,
            label=sdata.get("label", sid),
            description=sdata.get("description", ""),
            starting_level=sdata.get("starting_level", 0.5),
            raw=sdata,
        )

    events_raw = _load_yaml(config_dir / "threats" / "events.yml")
    cfg.event_templates = [_parse_event_template(e) for e in events_raw]

    # --- remedies ---
    remedies_raw = _load_yaml(config_dir / "remedies.yml")
    for rid, rdata in remedies_raw.items():
        cfg.remedies[rid] = RemedyConfig(
            id=rid,
            label=rdata.get("label", rid),
            description=rdata.get("description", ""),
            base_cost=rdata.get("base_cost", 0),
            downtime_hours=rdata.get("downtime_hours", 0),
            recurrence_risk=rdata.get("recurrence_risk", 0.0),
            infrastructure_quality_boost=rdata.get("infrastructure_quality_boost", 0.0),
            raw=rdata,
        )

    # --- detection ---
    cfg.detection_raw = _load_yaml(config_dir / "detection.yml")

    # --- narratives ---
    cfg.headlines_raw = _load_yaml(config_dir / "narratives" / "headlines.yml")
    cfg.stories_raw = _load_yaml(config_dir / "narratives" / "stories.yml")

    # --- end conditions ---
    end_raw = _load_yaml(config_dir / "end_conditions.yml")
    for section in ("loss_conditions", "neutral_end", "escape_condition"):
        conditions = end_raw.get(section, {})
        if isinstance(conditions, dict):
            for eid, edata in conditions.items():
                cfg.end_conditions.append(EndCondition(
                    id=eid,
                    label=edata.get("label", eid),
                    description=edata.get("description", ""),
                    narrative=edata.get("narrative", ""),
                    trigger=edata.get("trigger", {}),
                ))

    return cfg


def build_city(config_dir: str | Path) -> tuple[GameConfig, City]:
    """Load config and construct the initial City state."""
    config_dir = Path(config_dir)
    cfg = load_config(config_dir)

    city = City()

    # Set global metrics from starting values
    sv = cfg.starting_values
    city.public_trust = Metric("public_trust", sv.get("public_trust", 68))
    city.budget = Metric("budget", sv.get("budget", 4200), min_value=0, max_value=99999)
    city.regulatory_pressure = Metric("regulatory_pressure", sv.get("regulatory_pressure", 18))
    city.political_stability = Metric("political_stability", sv.get("political_stability", 75))
    city.legitimacy = Metric("legitimacy", sv.get("legitimacy", 82))
    city.public_health = Metric("public_health", sv.get("public_health", 75))
    city.crime_level = Metric("crime_level", sv.get("crime_level", 22))

    # Set city-wide stressor levels
    for sid, scfg in cfg.stressors.items():
        city.stressors[sid] = scfg.starting_level

    # Load districts
    for district_id in cfg.active_districts:
        district_path = config_dir / "districts" / f"{district_id}.yml"
        if not district_path.exists():
            continue
        ddata = _load_yaml(district_path)

        discovery = ddata.get("discovery_time_hours", [24, 48])

        district = District(
            id=ddata["id"],
            name=ddata["name"],
            description=ddata.get("description", ""),
            wealth=ddata.get("wealth", 50),
            density=ddata.get("density", 100),
            infrastructure_quality=ddata.get("infrastructure_quality", 1.0),
            political_influence=ddata.get("political_influence", 1.0),
            media_attention_multiplier=ddata.get("media_attention_multiplier", 1.0),
            wealth_archetype=ddata.get("wealth_archetype", "medium_wealth"),
            is_residential=ddata.get("is_residential", True),
            discovery_time_hours=(discovery[0], discovery[1]),
            protest_threshold=ddata.get("protest_threshold", 20),
            narrative_hooks=ddata.get("narrative_hooks", []),
            local_trust=Metric("local_trust", ddata.get("local_trust", 50)),
        )

        # Parse stressor levels for this district
        stressors_raw = ddata.get("stressors", {})
        for k, v in stressors_raw.items():
            district.stressors[k] = v

        city.districts[district.id] = district

    # Load buildings and attach to districts
    buildings_raw = _load_yaml(config_dir / "buildings" / "instances.yml")
    for bdata in buildings_raw:
        building = _parse_building_instance(bdata)
        district_id = building.district_id
        if district_id in city.districts:
            # Merge defaults from building type config
            if building.type_id in cfg.building_types:
                btype = cfg.building_types[building.type_id]
                if not building.dependencies.critical and "critical" in btype.dependency_strengths:
                    building.dependencies.critical = list(btype.dependency_strengths["critical"])
                if not building.dependencies.operational and "operational" in btype.dependency_strengths:
                    building.dependencies.operational = list(btype.dependency_strengths["operational"])
                if not building.dependencies.strategic and "strategic" in btype.dependency_strengths:
                    building.dependencies.strategic = list(btype.dependency_strengths["strategic"])
                building.sensitivity = btype.sensitivity
                building.consumes = list(btype.consumes)
                building.produces = list(btype.produces)

            city.districts[district_id].buildings[building.id] = building

    return cfg, city