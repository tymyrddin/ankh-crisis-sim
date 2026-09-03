from pathlib import Path

from src.config.loader import build_city
from src.engine.clock import ClockState, GameClock
from src.engine.simulation import Simulation

CONFIG_DIR = Path(__file__).parent.parent.parent / "config"


class TestGameClock:
    def test_initial_state(self):
        clock = GameClock()
        assert clock.tick == 0
        assert clock.state == ClockState.PAUSED
        assert clock.day == 1

    def test_advance(self):
        clock = GameClock(ticks_per_day=24)
        clock.advance()
        assert clock.tick == 1
        assert clock.hour == (clock.starting_hour + 1) % 24

    def test_day_calculation(self):
        clock = GameClock(ticks_per_day=24, starting_day=1, starting_hour=0)
        for _ in range(24):
            clock.advance()
        assert clock.day == 2

    def test_pause_resume(self):
        clock = GameClock()
        clock.resume()
        assert clock.is_running
        clock.pause()
        assert not clock.is_running


class TestSimulation:
    def test_initialise(self):
        sim = Simulation(CONFIG_DIR)
        sim.initialise()
        assert sim.city is not None
        assert len(sim.city.districts) == 8

    def test_tick_advances_clock(self):
        sim = Simulation(CONFIG_DIR)
        sim.initialise()
        result = sim.tick()
        assert result.tick == 1

    def test_multiple_ticks(self):
        sim = Simulation(CONFIG_DIR)
        sim.initialise()
        for _ in range(100):
            result = sim.tick()
        assert result.tick == 100

    def test_apply_remedy_unknown_event(self):
        sim = Simulation(CONFIG_DIR)
        sim.initialise()
        result = sim.apply_remedy("nonexistent", "technical_restoration")
        assert not result.success

    def test_get_visible_events_initially_empty(self):
        sim = Simulation(CONFIG_DIR)
        sim.initialise()
        events = sim.get_visible_events()
        assert len(events) == 0


class TestMetrics:
    def test_metric_apply(self):
        from src.models.metric import Metric
        m = Metric("test", 50.0, min_value=0, max_value=100)
        m.apply(-10, tick=1, cause="test")
        assert m.value == 40.0
        assert len(m.history) == 1

    def test_metric_clamp(self):
        from src.models.metric import Metric
        m = Metric("test", 5.0, min_value=0, max_value=100)
        m.apply(-20, tick=1)
        assert m.value == 0.0

    def test_metric_history(self):
        from src.models.metric import Metric
        m = Metric("test", 50.0)
        m.apply(-5, tick=1, cause="event_a")
        m.apply(-3, tick=2, cause="event_b")
        assert len(m.history) == 2
        assert m.history[0].cause == "event_a"
        assert m.history[1].value == 42.0


class TestBuilding:
    def test_fail_and_restore(self):
        from src.models.building import Building
        b = Building(id="test", name="Test", type_id="tavern", district_id="small_gods", position=(0, 0))
        assert b.is_operational
        b.fail(tick=1, event_id="evt1")
        assert b.is_failed
        b.restore(recurrence_risk=0.3)
        assert b.is_operational
        assert b.recurrence_risk == 0.3


class TestDistrict:
    def test_failure_probability_modifier(self):
        _, city = build_city(CONFIG_DIR)
        nap = city.districts["nap_hill"]
        shades = city.districts["the_shades"]
        assert nap.failure_probability_modifier < shades.failure_probability_modifier

    def test_is_in_crisis(self):
        _, city = build_city(CONFIG_DIR)
        shades = city.districts["the_shades"]
        assert not shades.is_in_crisis
        for b in shades.buildings.values():
            b.fail(tick=1, event_id="test")
        assert shades.is_in_crisis


class TestEndConditions:
    def test_no_end_at_start(self):
        from src.engine.end_check import check_end_conditions
        cfg, city = build_city(CONFIG_DIR)
        result = check_end_conditions(cfg, city, elapsed_days=0)
        assert result is None

    def test_bankruptcy_triggers(self):
        from src.engine.end_check import check_end_conditions
        from src.models.metric import Metric, MetricSnapshot
        cfg, city = build_city(CONFIG_DIR)
        # a budget that allows debt
        city.budget = Metric("budget", -100, min_value=-10000, max_value=99999)
        # 15 days of hourly snapshots
        for i in range(24 * 15):
            city.budget.history.append(MetricSnapshot(tick=i, value=-100))
        result = check_end_conditions(cfg, city, elapsed_days=30)
        assert result is not None
        assert result.condition_id == "bankruptcy"
