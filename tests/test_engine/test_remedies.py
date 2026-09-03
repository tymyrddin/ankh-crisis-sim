from pathlib import Path

from src.config.loader import build_city, EventTemplate
from src.engine.events import _find_target_building
from src.engine.remedies import apply_remedy, process_remedy_completions
from src.models.event import EventPhase, GameEvent

CONFIG_DIR = Path(__file__).parent.parent.parent / "config"


def _make_event(building_id: str, district_id: str, tick: int = 1) -> GameEvent:
    return GameEvent(
        id="test_evt_1",
        template_id="pump_failure",
        name="Test Pump Failure",
        category="degradation_and_neglect",
        domain="water",
        phase=EventPhase.DETECTED,
        target_district_id=district_id,
        target_building_id=building_id,
        created_tick=tick,
        detected_tick=tick + 4,
    )


class TestApplyRemedy:
    def test_emergency_patch_deducts_cost(self):
        cfg, city = build_city(CONFIG_DIR)
        district = next(iter(city.districts.values()))
        building = next(iter(district.buildings.values()))
        building.fail(tick=1, event_id="test_evt_1")

        event = _make_event(building.id, district.id)
        city.events.append(event)
        budget_before = city.budget.value

        result = apply_remedy(cfg, city, event, "technical_restoration", tick=10)

        assert result.success
        assert city.budget.value < budget_before

    def test_emergency_patch_sets_responding_phase(self):
        cfg, city = build_city(CONFIG_DIR)
        district = next(iter(city.districts.values()))
        building = next(iter(district.buildings.values()))
        building.fail(tick=1, event_id="test_evt_1")

        event = _make_event(building.id, district.id)
        city.events.append(event)

        apply_remedy(cfg, city, event, "technical_restoration", tick=10)

        assert event.phase == EventPhase.RESPONDING
        assert event.remedy_applied == "technical_restoration"

    def test_remedy_records_applied_tick(self):
        cfg, city = build_city(CONFIG_DIR)
        district = next(iter(city.districts.values()))
        building = next(iter(district.buildings.values()))
        building.fail(tick=1, event_id="test_evt_1")

        event = _make_event(building.id, district.id)
        city.events.append(event)

        apply_remedy(cfg, city, event, "technical_restoration", tick=10)

        assert event.remedy_applied_tick == 10

    def test_cannot_remedy_hidden_event(self):
        cfg, city = build_city(CONFIG_DIR)
        district = next(iter(city.districts.values()))
        building = next(iter(district.buildings.values()))
        building.fail(tick=1, event_id="test_evt_1")

        event = _make_event(building.id, district.id)
        event.phase = EventPhase.HIDDEN
        city.events.append(event)

        result = apply_remedy(cfg, city, event, "technical_restoration", tick=10)
        assert not result.success

    def test_insufficient_budget_fails(self):
        cfg, city = build_city(CONFIG_DIR)
        district = next(iter(city.districts.values()))
        building = next(iter(district.buildings.values()))
        building.fail(tick=1, event_id="test_evt_1")

        event = _make_event(building.id, district.id)
        city.events.append(event)

        city.budget.apply(city.budget.min_value - city.budget.value, tick=1, cause="drain")

        result = apply_remedy(cfg, city, event, "resilience_investment", tick=10)
        assert not result.success
        assert "Insufficient" in result.message

    def test_spending_can_run_budget_below_zero(self):
        cfg, city = build_city(CONFIG_DIR)
        assert city.budget.min_value < 0
        district = next(iter(city.districts.values()))
        building = next(iter(district.buildings.values()))
        building.fail(tick=1, event_id="test_evt_1")

        event = _make_event(building.id, district.id)
        city.events.append(event)

        # Leave less than the remedy costs, but within the credit floor
        city.budget.apply(-city.budget.value, tick=1, cause="drain")
        city.budget.apply(10, tick=1, cause="pocket change")

        result = apply_remedy(cfg, city, event, "technical_restoration", tick=10)
        assert result.success
        assert city.budget.value < 0
        assert city.budget.value >= city.budget.min_value


class TestCostModifiers:
    def _cost_in(self, district_id: str) -> float:
        cfg, city = build_city(CONFIG_DIR)
        district = city.districts[district_id]
        building = next(iter(district.buildings.values()))
        building.fail(tick=1, event_id="test_evt_1")
        event = _make_event(building.id, district.id)
        city.events.append(event)
        result = apply_remedy(cfg, city, event, "technical_restoration", tick=10)
        assert result.success
        return result.cost

    def test_worse_infrastructure_costs_more_to_patch(self):
        cfg, _ = build_city(CONFIG_DIR)
        base = cfg.remedies["technical_restoration"].base_cost
        shades = self._cost_in("the_shades")       # infrastructure_quality 3.0
        nap_hill = self._cost_in("nap_hill")       # infrastructure_quality 0.3
        assert shades > base > nap_hill

    def test_zero_downtime_resolves_immediately(self):
        cfg, city = build_city(CONFIG_DIR)
        district = next(iter(city.districts.values()))
        building = next(iter(district.buildings.values()))
        building.fail(tick=1, event_id="test_evt_1")

        event = _make_event(building.id, district.id)
        city.events.append(event)

        apply_remedy(cfg, city, event, "public_compensation", tick=10)

        assert event.phase == EventPhase.RESOLVED
        assert building.is_operational


class TestRemedyCompletion:
    def test_completion_uses_applied_tick_not_detected_tick(self):
        cfg, city = build_city(CONFIG_DIR)
        # Zero stressors that extend downtime so the base 4h is deterministic
        city.stressors["underinvestment"] = 0.0
        city.stressors["organisational_fragmentation"] = 0.0
        district = next(iter(city.districts.values()))
        building = next(iter(district.buildings.values()))
        building.fail(tick=1, event_id="test_evt_1")

        event = _make_event(building.id, district.id, tick=1)
        event.detected_tick = 5
        city.events.append(event)

        apply_remedy(cfg, city, event, "technical_restoration", tick=20)
        assert event.phase == EventPhase.RESPONDING
        assert event.remedy_applied_tick == 20

        completed = process_remedy_completions(cfg, city, tick=23)
        assert len(completed) == 0
        assert event.phase == EventPhase.RESPONDING

        completed = process_remedy_completions(cfg, city, tick=24)
        assert len(completed) == 1
        assert event.phase == EventPhase.RESOLVED

    def test_completion_returns_event(self):
        cfg, city = build_city(CONFIG_DIR)
        city.stressors["underinvestment"] = 0.0
        city.stressors["organisational_fragmentation"] = 0.0
        district = next(iter(city.districts.values()))
        building = next(iter(district.buildings.values()))
        building.fail(tick=1, event_id="test_evt_1")

        event = _make_event(building.id, district.id)
        city.events.append(event)

        apply_remedy(cfg, city, event, "technical_restoration", tick=10)

        completed = process_remedy_completions(cfg, city, tick=14)
        assert len(completed) == 1
        msg, resolved_event = completed[0]
        assert resolved_event is event
        assert "resolved" in msg

    def test_building_restored_after_completion(self):
        cfg, city = build_city(CONFIG_DIR)
        city.stressors["underinvestment"] = 0.0
        city.stressors["organisational_fragmentation"] = 0.0
        district = next(iter(city.districts.values()))
        building = next(iter(district.buildings.values()))
        building.fail(tick=1, event_id="test_evt_1")

        event = _make_event(building.id, district.id)
        city.events.append(event)

        apply_remedy(cfg, city, event, "technical_restoration", tick=10)
        process_remedy_completions(cfg, city, tick=14)

        assert building.is_operational
        assert building.active_event_id is None

    def test_structural_upgrade_takes_longer(self):
        cfg, city = build_city(CONFIG_DIR)
        city.stressors["underinvestment"] = 0.0
        city.stressors["organisational_fragmentation"] = 0.0
        district = next(iter(city.districts.values()))
        building = next(iter(district.buildings.values()))
        building.fail(tick=1, event_id="test_evt_1")

        event = _make_event(building.id, district.id)
        city.events.append(event)

        apply_remedy(cfg, city, event, "resilience_investment", tick=10)

        completed = process_remedy_completions(cfg, city, tick=50)
        assert len(completed) == 0
        assert event.phase == EventPhase.RESPONDING

        completed = process_remedy_completions(cfg, city, tick=82)
        assert len(completed) == 1
        assert event.phase == EventPhase.RESOLVED


class TestRecurrenceRisk:
    def test_high_recurrence_risk_weighted_higher(self):
        cfg, city = build_city(CONFIG_DIR)
        # Use a filter-free template so all buildings are candidates regardless of type
        template = EventTemplate(
            id="test_recurrence",
            name="Test Recurrence",
            category="degradation_and_neglect",
        )

        district = next(iter(city.districts.values()))
        buildings = list(district.buildings.values())

        if len(buildings) < 2:
            return  # need at least 2 buildings for this test

        high_risk_building = buildings[0]
        high_risk_building.recurrence_risk = 1.0
        high_risk_building.active_event_id = None

        for b in buildings[1:]:
            b.recurrence_risk = 0.0
            b.active_event_id = None

        import random
        random.seed(42)

        hits = 0
        trials = 500
        for _ in range(trials):
            chosen = _find_target_building(template, city, district.id)
            if chosen and chosen.id == high_risk_building.id:
                hits += 1

        expected_ratio = 10.0 / (10.0 + len(buildings) - 1)
        actual_ratio = hits / trials
        assert actual_ratio > expected_ratio * 0.5, (
            f"High-risk building chosen {actual_ratio:.1%} vs expected ~{expected_ratio:.1%}"
        )