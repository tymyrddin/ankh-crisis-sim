from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

from src.models.building import Building, BuildingStatus, DependencyStrengths
from src.models.city import City
from src.models.district import District
from src.models.event import DelayedEffect, MetricEffect
from src.models.metric import Metric


def _load_yaml(path: Path) -> Any:
    with open(path, encoding="utf-8") as f:
        return yaml.safe_load(f)


def _load_mapping(path: Path) -> dict[str, Any]:
    data = _load_yaml(path)
    if not isinstance(data, dict):
        raise ValueError(f"{path} needs a mapping at top level")
    return data


def _load_list(path: Path) -> list[Any]:
    data = _load_yaml(path)
    if not isinstance(data, list):
        raise ValueError(f"{path} needs a list at top level")
    return data


@dataclass
class TimeConfig:
    ticks_per_day: int = 24
    starting_day: int = 1
    starting_hour: int = 8


@dataclass
class SpeedConfig:
    seconds_per_game_hour: float = 1.0
    default_multiplier: float = 1.0
    fast_multiplier: float = 10.0


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

    immediate_effects: list[MetricEffect] = field(default_factory=list)
    delayed_effects: list[DelayedEffect] = field(default_factory=list)
    duration_penalty_per_day: float = 0.0
    duration_penalty_metric: str = "local_trust"
    cascade_dependency: str | None = None
    cascade_scope: str = "neighbours"
    residential_impact: bool = False
    discovery_hours: tuple[float, float] | None = None  # replaces the district range when set


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
class GameSettings:
    event_rate_multiplier: float = 0.3  # fraction of base event probability
    discovery_speed_multiplier: float = 1.0  # above 1 keeps events hidden longer
    cascade_multiplier: float = 1.0
    game_duration_days: int = 0  # seeded from the days_elapsed end condition at load


@dataclass
class EndCondition:
    id: str
    label: str
    description: str = ""
    narrative: str = ""
    trigger: dict = field(default_factory=dict)
    min_days: int = 0


@dataclass
class GameConfig:
    time: TimeConfig = field(default_factory=TimeConfig)
    speed: SpeedConfig = field(default_factory=SpeedConfig)
    settings: GameSettings = field(default_factory=GameSettings)
    active_districts: list[str] = field(default_factory=list)
    remedies: dict[str, RemedyConfig] = field(default_factory=dict)
    event_templates: list[EventTemplate] = field(default_factory=list)
    stressors: dict[str, StressorConfig] = field(default_factory=dict)
    building_types: dict[str, BuildingTypeConfig] = field(default_factory=dict)
    end_conditions: list[EndCondition] = field(default_factory=list)
    metrics_global_raw: dict = field(default_factory=dict)
    headlines_raw: dict = field(default_factory=dict)
    stories_raw: dict = field(default_factory=dict)
    starting_values: dict[str, float] = field(default_factory=dict)
    budget_income: dict = field(default_factory=dict)
    budget_raw: dict = field(default_factory=dict)
    postgame: dict = field(default_factory=dict)

    def template(self, template_id: str) -> EventTemplate | None:
        return next((t for t in self.event_templates if t.id == template_id), None)


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
        stressor_amplifiers=raw.get("stressor_amplifiers") or {},
        headlines=raw.get("headlines", []),
        stories=raw.get("stories", []),
        residential_impact=raw.get("residential_impact", False),
        raw=raw,
    )
    if "discovery_hours" in raw:
        lo, hi = raw["discovery_hours"]
        tmpl.discovery_hours = (float(lo), float(hi))

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
    )


def load_config(config_dir: str | Path) -> GameConfig:
    config_dir = Path(config_dir)
    cfg = GameConfig()

    game_raw = _load_mapping(config_dir / "game.yml")
    time_raw = game_raw.get("time", {})
    cfg.time = TimeConfig(
        ticks_per_day=time_raw.get("ticks_per_day", 24),
        starting_day=time_raw.get("starting_day", 1),
        starting_hour=time_raw.get("starting_hour", 8),
    )
    speed_raw = game_raw.get("speed", {})
    cfg.speed = SpeedConfig(
        seconds_per_game_hour=speed_raw.get("seconds_per_game_hour", 1.0),
        default_multiplier=speed_raw.get("default_multiplier", 1.0),
        fast_multiplier=speed_raw.get("fast_multiplier", 10.0),
    )
    cfg.active_districts = game_raw.get("active_districts", [])
    cfg.starting_values = game_raw.get("starting_values", {})
    budget_section = game_raw.get("budget", {})
    cfg.budget_income = budget_section.get("income_per_month", {})
    cfg.budget_raw = budget_section

    cfg.metrics_global_raw = _load_mapping(config_dir / "metrics" / "global.yml")

    types_raw = _load_mapping(config_dir / "buildings" / "_types.yml")
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

    cfg.stressors = {}
    stressors_raw = _load_mapping(config_dir / "threats" / "stressors.yml")
    for sid, sdata in stressors_raw.items():
        cfg.stressors[sid] = StressorConfig(
            id=sid,
            label=sdata.get("label", sid),
            description=sdata.get("description", ""),
            starting_level=sdata.get("starting_level", 0.5),
            raw=sdata,
        )

    events_raw = _load_list(config_dir / "threats" / "events.yml")
    cfg.event_templates = [_parse_event_template(e) for e in events_raw]

    remedies_raw = _load_mapping(config_dir / "remedies.yml")
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

    cfg.headlines_raw = _load_mapping(config_dir / "narratives" / "headlines.yml")
    cfg.stories_raw = _load_mapping(config_dir / "narratives" / "stories.yml")

    end_raw = _load_mapping(config_dir / "end_conditions.yml")
    cfg.postgame = end_raw.get("postgame", {})
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
                    min_days=int(edata.get("min_days", 0)),
                ))

    # the settings popup adjusts the term at runtime; the YAML condition is the starting value
    for cond in cfg.end_conditions:
        if isinstance(cond.trigger, dict) and "days_elapsed" in cond.trigger:
            cfg.settings.game_duration_days = int(cond.trigger["days_elapsed"])
            break

    return cfg


def build_city(config_dir: str | Path) -> tuple[GameConfig, City]:
    config_dir = Path(config_dir)
    cfg = load_config(config_dir)

    city = City()

    # bounds from metrics/global.yml; starting value from game.yml, falling back to global.yml
    for name in ("public_trust", "budget", "regulatory_pressure", "political_stability",
                 "legitimacy", "public_health", "crime_level"):
        spec = cfg.metrics_global_raw.get(name, {})
        setattr(city, name, Metric(
            name,
            float(cfg.starting_values.get(name, spec.get("starting", 0))),
            min_value=float(spec.get("min", 0)),
            max_value=float(spec.get("max", 100)),
        ))

    for sid, scfg in cfg.stressors.items():
        city.stressors[sid] = scfg.starting_level

    for district_id in cfg.active_districts:
        district_path = config_dir / "districts" / f"{district_id}.yml"
        if not district_path.exists():
            continue
        ddata = _load_mapping(district_path)

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
            local_trust=Metric("local_trust", ddata.get("local_trust", 50)),
        )

        stressors_raw = ddata.get("stressors", {})
        for k, v in stressors_raw.items():
            district.stressors[k] = v

        city.districts[district.id] = district

    buildings_raw = _load_list(config_dir / "buildings" / "instances.yml")
    for bdata in buildings_raw:
        building = _parse_building_instance(bdata)
        district_id = building.district_id
        if district_id in city.districts:
            # type defaults fill in what the instance leaves blank
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
                building.detection_time_modifier = btype.detection_time_modifier
            override = bdata.get("detection_time_modifier_override")
            if override is not None:
                building.detection_time_modifier = float(override)

            city.districts[district_id].buildings[building.id] = building

    return cfg, city
