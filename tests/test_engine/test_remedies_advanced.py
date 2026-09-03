from __future__ import annotations

import random
from pathlib import Path

from src.config.loader import build_city
from src.engine.metrics import apply_passive_dynamics
from src.engine.remedies import apply_remedy, process_remedy_completions
from src.models.event import EventPhase, GameEvent

CONFIG_DIR = Path(__file__).parent.parent.parent / "config"


def _make_event(
    building_id: str,
    district_id: str,
    tick: int = 1,
    event_id: str = "test_evt_adv",
) -> GameEvent:
    return GameEvent(
        id=event_id,
        template_id="pump_failure",
        name="Test Failure",
        category="degradation_and_neglect",
        domain="water",
        phase=EventPhase.DETECTED,
        target_district_id=district_id,
        target_building_id=building_id,
        created_tick=tick,
        detected_tick=tick + 4,
    )


def _setup_event_in_district(district_id: str = "the_shades"):
    cfg, city = build_city(CONFIG_DIR)
    # Neutralise stressors that perturb downtime so test arithmetic is deterministic
    city.stressors["underinvestment"] = 0.0
    city.stressors["organisational_fragmentation"] = 0.0
    district = city.districts[district_id]
    building = next(iter(district.buildings.values()))
    building.fail(tick=1, event_id="test_evt_adv")
    event = _make_event(building.id, district_id)
    city.events.append(event)
    return cfg, city, event, district, building


class TestPressStatementWindow:
    def test_window_in_progress_keeps_responding(self):
        cfg, city, event, district, _ = _setup_event_in_district()
        trust_before = district.local_trust.value

        apply_remedy(cfg, city, event, "press_statement", tick=10)
        assert event.phase == EventPhase.RESPONDING

        # 24 hours later: still inside the 48h window, no penalty yet
        process_remedy_completions(cfg, city, tick=34)
        assert event.phase == EventPhase.RESPONDING
        assert event.remedy_applied == "press_statement"
        assert district.local_trust.value == trust_before

    def test_window_expiry_reverts_to_detected_and_applies_penalty(self):
        cfg, city, event, district, _ = _setup_event_in_district()
        trust_before = district.local_trust.value

        apply_remedy(cfg, city, event, "press_statement", tick=10)
        # 49 hours after application: window closed, penalty fires
        completed = process_remedy_completions(cfg, city, tick=59)

        assert any("press statement" in msg.lower() for msg, _ in completed)
        assert event.phase == EventPhase.DETECTED
        assert event.remedy_applied is None
        assert event.remedy_applied_tick is None
        # the -10 penalty passes through media_attention and the inequality modifier, so check direction only
        assert district.local_trust.value < trust_before


class TestAccountabilityBackfire:
    def test_backfire_fires_when_rng_under_risk(self):
        cfg, city, event, district, _ = _setup_event_in_district("nap_hill")

        # backfire_risk = 0.25. With seed 4 the first random() is about 0.237
        random.seed(4)

        apply_remedy(cfg, city, event, "accountability_actions", tick=10)

        backfire_entries = [
            s for s in district.local_trust.history if "backfired" in s.cause
        ]
        assert len(backfire_entries) == 1
        public_backfire = [
            s for s in city.public_trust.history if "backfired" in s.cause
        ]
        assert len(public_backfire) == 1

    def test_no_backfire_when_rng_above_risk(self):
        cfg, city, event, district, _ = _setup_event_in_district("nap_hill")

        # with seed 0 the first random() is about 0.844
        random.seed(0)

        apply_remedy(cfg, city, event, "accountability_actions", tick=10)

        backfire_entries = [
            s for s in district.local_trust.history if "backfired" in s.cause
        ]
        assert backfire_entries == []


class TestDoNothing:
    def test_decay_multiplier_applies_immediate_penalty(self):
        cfg, city, event, district, _ = _setup_event_in_district()
        trust_before = district.local_trust.value

        apply_remedy(cfg, city, event, "do_nothing", tick=10)

        # decay_multiplier=2.0 gives -(2.0-1.0)*3 = -3 trust, modulated by media and inequality
        assert district.local_trust.value < trust_before

    def test_cascade_risk_boost_set_on_event(self):
        cfg, city, event, _, _ = _setup_event_in_district()

        apply_remedy(cfg, city, event, "do_nothing", tick=10)

        assert event.cascade_risk_boost == 1.5


class TestOperationalWorkaroundRiskTransfer:
    def test_risk_transfer_hits_another_district(self):
        cfg, city, event, target_district, _ = _setup_event_in_district("the_shades")

        other_trust = {
            d.id: d.local_trust.value
            for d in city.districts.values()
            if d.id != target_district.id
        }

        random.seed(42)
        apply_remedy(cfg, city, event, "operational_workaround", tick=10)

        dropped = [
            d.id for d in city.districts.values()
            if d.id != target_district.id and d.local_trust.value < other_trust[d.id]
        ]
        assert len(dropped) == 1


class TestPublicCompensationReversal:
    def test_duration_reversal_scheduled_as_delayed_effect(self):
        cfg, city, event, district, _ = _setup_event_in_district()

        apply_remedy(cfg, city, event, "public_compensation", tick=10)

        # public_compensation queues a DelayedEffect with delta=-immediate (i.e. -10)
        reversals = [
            de for de in event.delayed_effects
            for eff in de.effects
            if eff.metric == "local_trust" and eff.delta < 0 and eff.district_id == district.id
        ]
        assert len(reversals) == 1
        # delay_hours = duration_days*24 + (tick - created_tick) = 720 + 9 = 729
        assert reversals[0].delay_hours == 30 * 24 + (10 - 1)


class TestResilienceInvestmentInfrastructureBoost:
    def test_completion_reduces_infrastructure_quality_toward_baseline(self):
        cfg, city, event, district, _ = _setup_event_in_district("the_shades")
        iq_before = district.infrastructure_quality  # 3.0
        assert iq_before > 1.0

        # cost = 300 * wealth/50 = 60
        apply_remedy(cfg, city, event, "resilience_investment", tick=10)
        # 72h downtime completes at tick 82
        process_remedy_completions(cfg, city, tick=82)

        # boost 0.3 of excess 2.0 is a 0.6 reduction, new value 2.4
        assert district.infrastructure_quality < iq_before
        assert district.infrastructure_quality >= 1.0
        assert abs(district.infrastructure_quality - 2.4) < 0.01


class TestResilienceInvestmentDelayedTrust:
    def test_pending_trust_boost_queued_on_completion(self):
        cfg, city, event, district, _ = _setup_event_in_district("the_shades")
        district.pending_trust_boosts.clear()

        apply_remedy(cfg, city, event, "resilience_investment", tick=10)
        process_remedy_completions(cfg, city, tick=82)

        # delayed_days=14, scheduled at tick 82 + 336 = 418
        assert len(district.pending_trust_boosts) == 1
        scheduled_tick, amount, _ = district.pending_trust_boosts[0]
        assert scheduled_tick == 418
        assert amount == 8

    def test_pending_trust_boost_applied_at_scheduled_tick(self):
        cfg, city, event, district, _ = _setup_event_in_district("the_shades")

        apply_remedy(cfg, city, event, "resilience_investment", tick=10)
        process_remedy_completions(cfg, city, tick=82)
        trust_before_flush = district.local_trust.value

        # next daily boundary after 418 is 432
        apply_passive_dynamics(city, tick=432, ticks_per_day=24, cfg=cfg)

        assert district.local_trust.value > trust_before_flush
        assert district.pending_trust_boosts == []


class TestSocialInequalityShift:
    def test_resilience_investment_in_low_wealth_district_decreases_inequality(self):
        cfg, city, event, _, _ = _setup_event_in_district("the_shades")
        before = city.stressors["social_inequality"]

        apply_remedy(cfg, city, event, "resilience_investment", tick=10)

        # inequality_decrease = 0.03
        assert city.stressors["social_inequality"] < before
        assert abs(city.stressors["social_inequality"] - (before - 0.03)) < 1e-6

    def test_any_remedy_in_high_wealth_district_increases_inequality(self):
        cfg, city, event, _, _ = _setup_event_in_district("nap_hill")
        before = city.stressors["social_inequality"]

        apply_remedy(cfg, city, event, "technical_restoration", tick=10)

        # inequality_increase = 0.02
        assert city.stressors["social_inequality"] > before
        assert abs(city.stressors["social_inequality"] - (before + 0.02)) < 1e-6


class TestResilienceInvestmentStressorDecrease:
    def test_completion_decreases_underinvestment_stressor(self):
        cfg, city, event, district, _ = _setup_event_in_district("the_shades")
        # underinvestment was zeroed in setup; downtime is cached at apply time so
        # setting it now does not extend the repair
        apply_remedy(cfg, city, event, "resilience_investment", tick=10)
        city.stressors["underinvestment"] = 0.6

        process_remedy_completions(cfg, city, tick=82)

        # side_effect: stressor_decrease.underinvestment = 0.03
        assert city.stressors["underinvestment"] < 0.6
        assert abs(city.stressors["underinvestment"] - 0.57) < 1e-6
