from __future__ import annotations

from src.engine.clock import ClockState, GameClock


class TestAdvance:
    def test_advance_increments_tick(self):
        clock = GameClock()
        assert clock.tick == 0

        clock.advance()
        assert clock.tick == 1

        clock.advance()
        clock.advance()
        assert clock.tick == 3

    def test_advance_returns_new_tick(self):
        clock = GameClock()
        assert clock.advance() == 1
        assert clock.advance() == 2


class TestDayRollover:
    def test_day_rolls_over_at_ticks_per_day(self):
        clock = GameClock(ticks_per_day=24, starting_day=1)
        for _ in range(23):
            clock.advance()
        assert clock.day == 1

        clock.advance()
        assert clock.day == 2

    def test_starting_day_offset_respected(self):
        clock = GameClock(ticks_per_day=24, starting_day=5)
        assert clock.day == 5

        for _ in range(24):
            clock.advance()
        assert clock.day == 6

    def test_elapsed_days(self):
        clock = GameClock(ticks_per_day=24)
        for _ in range(48):
            clock.advance()
        assert clock.elapsed_days == 2


class TestHour:
    def test_hour_wraps_around_modulus(self):
        clock = GameClock(ticks_per_day=24, starting_hour=22)
        # starting_hour 22, tick 0 gives hour 22
        assert clock.hour == 22

        # (22 + 2) % 24 == 0
        clock.advance()
        clock.advance()
        assert clock.hour == 0


class TestTimeString:
    def test_time_string_format(self):
        clock = GameClock(starting_day=3, starting_hour=14)
        text = clock.time_string

        assert "Day 3" in text
        assert "14:00" in text


class TestPauseResume:
    def test_initial_state_paused(self):
        clock = GameClock()
        assert clock.state == ClockState.PAUSED
        assert not clock.is_running

    def test_resume_sets_running(self):
        clock = GameClock()
        clock.resume()
        assert clock.state == ClockState.RUNNING
        assert clock.is_running

    def test_pause_after_resume(self):
        clock = GameClock()
        clock.resume()
        clock.pause()
        assert clock.state == ClockState.PAUSED
        assert not clock.is_running


class TestSetSpeed:
    def test_set_speed_updates_multiplier(self):
        clock = GameClock()
        clock.set_speed(2.0)
        assert clock.speed_multiplier == 2.0

    def test_set_speed_clamps_to_minimum(self):
        clock = GameClock()
        clock.set_speed(0.0)
        assert clock.speed_multiplier == 0.1

        clock.set_speed(-1.0)
        assert clock.speed_multiplier == 0.1

    def test_set_speed_accepts_high_values(self):
        clock = GameClock()
        clock.set_speed(10.0)
        assert clock.speed_multiplier == 10.0
