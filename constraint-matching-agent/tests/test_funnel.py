"""Unit tests for the 4-layer constraint funnel engine."""

from __future__ import annotations

from datetime import date, timedelta

import pytest

from constraint_matching_agent.models.schemas import (
    AgentConfig,
    RecommendationCategory,
    RunningCapacityTracker,
    RunningShiftHours,
)
from constraint_matching_agent.funnel import (
    _determine_tier,
    check_equipment_compatibility,
    check_material_availability,
    check_utilization_and_workforce,
    derive_recommendation,
    evaluate_funnel,
    simulate_cascade,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

def _tracker(
    rm_normal=100.0, rm_ot=40.0, rm_wk=20.0,
    fl_normal=100.0, fl_ot=40.0, fl_wk=20.0,
    material=500.0, workforce=50,
) -> RunningCapacityTracker:
    return RunningCapacityTracker(
        session_id="test",
        rolling_mill_remaining_hrs=RunningShiftHours(
            normal_hrs=rm_normal, overtime_hrs=rm_ot,
            weekend_hrs=rm_wk,
            total_hrs=rm_normal + rm_ot + rm_wk,
        ),
        finishing_line_remaining_hrs=RunningShiftHours(
            normal_hrs=fl_normal, overtime_hrs=fl_ot,
            weekend_hrs=fl_wk,
            total_hrs=fl_normal + fl_ot + fl_wk,
        ),
        material_remaining_tons=material,
        workforce_remaining=workforce,
    )


def _equipment(
    rm_families=None, fl_families=None,
    gauge_min=None, gauge_max=None,
):
    rm_families = rm_families or ["Steel Coils", "Flat Bars"]
    fl_families = fl_families or ["Steel Coils", "Flat Bars"]
    rm = {
        "machine_type": "Rolling Mill",
        "product_families_supported": rm_families,
    }
    if gauge_min is not None:
        rm["gauge_range_min"] = gauge_min
    if gauge_max is not None:
        rm["gauge_range_max"] = gauge_max
    fl = {
        "machine_type": "Finishing Line",
        "product_families_supported": fl_families,
    }
    return [rm, fl]


def _order(
    order_id="PO-2026-001", product_family="Steel Coils",
    gauge=None, raw_material_tons=100.0,
    rolling_mill_hours=10.0, finishing_line_hours=8.0,
    due_date=None, priority="P1",
):
    due = due_date or (date.today() + timedelta(days=30)).isoformat()
    o = {
        "order_id": order_id,
        "product_family": product_family,
        "raw_material_tons": raw_material_tons,
        "rolling_mill_hours": rolling_mill_hours,
        "finishing_line_hours": finishing_line_hours,
        "due_date": due,
        "priority": priority,
    }
    if gauge is not None:
        o["gauge"] = gauge
    return o


def _config(**overrides) -> AgentConfig:
    return AgentConfig(**overrides)


# ---------------------------------------------------------------------------
# _determine_tier
# ---------------------------------------------------------------------------


class TestDetermineTier:
    def test_normal_sufficient(self):
        assert _determine_tier(10, 20, 10, 5) == "Normal"

    def test_normal_exact(self):
        assert _determine_tier(20, 20, 10, 5) == "Normal"

    def test_overtime_needed(self):
        assert _determine_tier(25, 20, 10, 5) == "Overtime"

    def test_weekend_needed(self):
        assert _determine_tier(32, 20, 10, 5) == "Weekend"

    def test_insufficient(self):
        assert _determine_tier(40, 20, 10, 5) == "Insufficient"

    def test_zero_required(self):
        assert _determine_tier(0, 20, 10, 5) == "Normal"


# ---------------------------------------------------------------------------
# Layer 1: Equipment Compatibility
# ---------------------------------------------------------------------------


class TestCheckEquipmentCompatibility:
    def test_pass_both_machines(self):
        r = check_equipment_compatibility(
            _order(product_family="Steel Coils"),
            _equipment(),
        )
        assert r.passed is True
        assert r.rolling_mill_compatible is True
        assert r.finishing_line_compatible is True
        assert r.failure_reason is None

    def test_fail_rolling_mill(self):
        r = check_equipment_compatibility(
            _order(product_family="Widgets"),
            _equipment(),
        )
        assert r.passed is False
        assert r.rolling_mill_compatible is False
        assert "Widgets" in r.failure_reason

    def test_fail_finishing_line(self):
        r = check_equipment_compatibility(
            _order(product_family="Steel Coils"),
            _equipment(fl_families=["Flat Bars"]),
        )
        assert r.passed is False
        assert r.finishing_line_compatible is False

    def test_gauge_in_range(self):
        r = check_equipment_compatibility(
            _order(gauge=2.5),
            _equipment(gauge_min=1.0, gauge_max=5.0),
        )
        assert r.passed is True
        assert r.gauge_in_range is True
        assert r.gauge_machine_min == 1.0
        assert r.gauge_machine_max == 5.0

    def test_gauge_out_of_range(self):
        r = check_equipment_compatibility(
            _order(gauge=6.0),
            _equipment(gauge_min=1.0, gauge_max=5.0),
        )
        assert r.passed is False
        assert r.gauge_in_range is False
        assert "6.0mm outside range" in r.failure_reason

    def test_no_gauge_range_defined(self):
        r = check_equipment_compatibility(
            _order(gauge=3.0),
            _equipment(),
        )
        assert r.passed is True
        assert r.gauge_in_range is True

    def test_no_gauge_on_order(self):
        r = check_equipment_compatibility(
            _order(),
            _equipment(gauge_min=1.0, gauge_max=5.0),
        )
        assert r.passed is True

    def test_empty_equipment_list(self):
        r = check_equipment_compatibility(_order(), [])
        assert r.passed is True


# ---------------------------------------------------------------------------
# Layer 2: Material Availability
# ---------------------------------------------------------------------------


class TestCheckMaterialAvailability:
    def test_full_match(self):
        t = _tracker(material=200.0)
        r = check_material_availability(
            _order(raw_material_tons=100.0), {}, t,
        )
        assert r.passed is True
        assert r.match_status == "Full Match"
        assert r.shortfall_tons == 0.0

    def test_partial_match_feasible(self):
        due = (date.today() + timedelta(days=30)).isoformat()
        t = _tracker(material=50.0)
        r = check_material_availability(
            _order(raw_material_tons=100.0, due_date=due),
            {"procurement_lead_time_days": 5, "net_available_hours_per_week": 40},
            t,
        )
        assert r.passed is True
        assert r.match_status == "Partial Match"
        assert r.shortfall_tons == 50.0
        assert r.procurement_feasible is True

    def test_no_match_deadline_exceeded(self):
        due = (date.today() + timedelta(days=2)).isoformat()
        t = _tracker(material=10.0)
        r = check_material_availability(
            _order(raw_material_tons=100.0, due_date=due,
                   rolling_mill_hours=40.0, finishing_line_hours=40.0),
            {"procurement_lead_time_days": 10, "net_available_hours_per_week": 40},
            t,
        )
        assert r.passed is False
        assert r.match_status == "No Match"
        assert r.procurement_feasible is False

    def test_exact_material_match(self):
        t = _tracker(material=100.0)
        r = check_material_availability(
            _order(raw_material_tons=100.0), {}, t,
        )
        assert r.passed is True
        assert r.match_status == "Full Match"

    def test_zero_material_required(self):
        t = _tracker(material=0.0)
        r = check_material_availability(
            _order(raw_material_tons=0.0), {}, t,
        )
        assert r.passed is True
        assert r.match_status == "Full Match"

    def test_invalid_due_date(self):
        t = _tracker(material=10.0)
        r = check_material_availability(
            _order(raw_material_tons=100.0, due_date="invalid"),
            {"procurement_lead_time_days": 1},
            t,
        )
        assert r.days_until_due_date == 0


# ---------------------------------------------------------------------------
# Layer 3: Utilization + Workforce
# ---------------------------------------------------------------------------


class TestCheckUtilizationAndWorkforce:
    def test_normal_shift_sufficient(self):
        t = _tracker(rm_normal=50, fl_normal=50, workforce=100)
        r = check_utilization_and_workforce(
            _order(rolling_mill_hours=10, finishing_line_hours=8),
            t,
            {"operators_per_rolling_mill": 1, "operators_per_finishing_line": 1},
            _config(),
        )
        assert r.passed is True
        assert r.recommended_shift_tier == "Normal"
        assert r.shift_escalation_needed is False

    def test_overtime_needed(self):
        t = _tracker(rm_normal=5, rm_ot=20, fl_normal=50, workforce=100)
        r = check_utilization_and_workforce(
            _order(rolling_mill_hours=10, finishing_line_hours=8),
            t,
            {"operators_per_rolling_mill": 1, "operators_per_finishing_line": 1},
            _config(),
        )
        assert r.passed is True
        assert r.shift_escalation_needed is True
        assert r.recommended_shift_tier in ("Overtime", "Weekend")

    def test_weekend_needed(self):
        t = _tracker(rm_normal=2, rm_ot=3, rm_wk=20, fl_normal=50, workforce=100)
        r = check_utilization_and_workforce(
            _order(rolling_mill_hours=10, finishing_line_hours=8),
            t,
            {"operators_per_rolling_mill": 1, "operators_per_finishing_line": 1},
            _config(),
        )
        assert r.passed is True
        assert r.shift_escalation_needed is True

    def test_insufficient_hours(self):
        t = _tracker(rm_normal=1, rm_ot=1, rm_wk=1, fl_normal=50, workforce=100)
        r = check_utilization_and_workforce(
            _order(rolling_mill_hours=10, finishing_line_hours=8),
            t,
            {"operators_per_rolling_mill": 1, "operators_per_finishing_line": 1},
            _config(),
        )
        assert r.passed is False
        assert "Insufficient" in (r.failure_reason or "")

    def test_workforce_hard_fail_normal(self):
        t = _tracker(rm_normal=50, fl_normal=50, workforce=0)
        r = check_utilization_and_workforce(
            _order(rolling_mill_hours=10, finishing_line_hours=8),
            t,
            {"operators_per_rolling_mill": 1, "operators_per_finishing_line": 1},
            _config(),
        )
        assert r.passed is False
        assert r.workforce_sufficient is False
        assert r.workforce_constraint_type == "hard"

    def test_workforce_soft_warning_overtime(self):
        t = _tracker(rm_normal=5, rm_ot=20, fl_normal=50, workforce=0)
        r = check_utilization_and_workforce(
            _order(rolling_mill_hours=10, finishing_line_hours=8),
            t,
            {"operators_per_rolling_mill": 1, "operators_per_finishing_line": 1},
            _config(),
        )
        assert r.passed is True
        assert r.workforce_sufficient is False
        assert r.workforce_constraint_type == "soft"

    def test_utilization_warning(self):
        # Only normal hours so total = normal, consuming 11/12 = 91.7% > 90%
        t = _tracker(rm_normal=12, rm_ot=0, rm_wk=0,
                     fl_normal=12, fl_ot=0, fl_wk=0, workforce=100)
        r = check_utilization_and_workforce(
            _order(rolling_mill_hours=11, finishing_line_hours=11),
            t,
            {"operators_per_rolling_mill": 1, "operators_per_finishing_line": 1},
            _config(utilization_warning_pct=0.90),
        )
        assert r.utilization_warning is True

    def test_escalation_options_populated(self):
        t = _tracker(rm_normal=5, rm_ot=20, rm_wk=10, fl_normal=50, workforce=100)
        r = check_utilization_and_workforce(
            _order(rolling_mill_hours=10, finishing_line_hours=8),
            t,
            {"operators_per_rolling_mill": 1, "operators_per_finishing_line": 1},
            _config(),
        )
        assert r.passed is True
        assert len(r.escalation_options) >= 1


# ---------------------------------------------------------------------------
# Layer 4: Cascade Impact Simulation
# ---------------------------------------------------------------------------


def _ohio_order(
    order_id="PO-2026-100", rm_hrs=5.0, fl_hrs=4.0,
    due_days=20, penalty=False, position=1,
):
    return {
        "order_id": order_id,
        "rolling_mill_hours": rm_hrs,
        "finishing_line_hours": fl_hrs,
        "due_date": (date.today() + timedelta(days=due_days)).isoformat(),
        "penalty_clause": penalty,
        "schedule_position": position,
        "customer_id": "C-001",
        "customer_tier": "Tier1",
    }


class TestSimulateCascade:
    def test_no_ohio_orders(self):
        r = simulate_cascade(_order(), [], _config())
        assert r.passed is True
        assert r.total_orders_impacted == 0

    def test_no_impact(self):
        ohio = [_ohio_order(due_days=60, position=1)]
        r = simulate_cascade(
            _order(rolling_mill_hours=2, finishing_line_hours=2),
            ohio, _config(),
        )
        assert r.passed is True
        assert r.total_orders_impacted == 0

    def test_impact_no_penalty(self):
        ohio = [
            _ohio_order(
                order_id="PO-2026-100", rm_hrs=5, fl_hrs=5,
                due_days=1, penalty=False, position=1,
            ),
        ]
        r = simulate_cascade(
            _order(rolling_mill_hours=20, finishing_line_hours=20),
            ohio, _config(),
        )
        assert r.passed is True
        assert r.total_orders_impacted >= 0
        assert r.has_penalty_risk is False

    def test_impact_with_penalty(self):
        ohio = [
            _ohio_order(
                order_id="PO-2026-100", rm_hrs=5, fl_hrs=5,
                due_days=1, penalty=True, position=1,
            ),
        ]
        r = simulate_cascade(
            _order(rolling_mill_hours=50, finishing_line_hours=50),
            ohio, _config(),
        )
        if r.total_orders_impacted > 0 and r.has_penalty_risk:
            assert r.passed is False
            assert r.failure_reason is not None

    def test_timeout_returns_partial(self, monkeypatch):
        """Patch time.monotonic to simulate immediate timeout."""
        import constraint_matching_agent.funnel as funnel_mod

        call_count = 0
        def fake_monotonic():
            nonlocal call_count
            call_count += 1
            # First call returns 0 (start), subsequent calls exceed timeout
            return 0.0 if call_count <= 1 else 100.0

        monkeypatch.setattr(funnel_mod.time, "monotonic", fake_monotonic)

        ohio = [
            _ohio_order(
                order_id=f"PO-2026-{i:03d}", rm_hrs=1, fl_hrs=1,
                due_days=1, penalty=False, position=i,
            )
            for i in range(100, 110)
        ]
        r = simulate_cascade(
            _order(rolling_mill_hours=500, finishing_line_hours=500),
            ohio,
            _config(cascade_timeout_secs=1),
        )
        assert r.timed_out is True

    def test_cascade_depth_limited(self):
        ohio = [
            _ohio_order(
                order_id=f"PO-2026-{i:03d}", rm_hrs=2, fl_hrs=2,
                due_days=3, penalty=False, position=i,
            )
            for i in range(100, 110)
        ]
        r = simulate_cascade(
            _order(rolling_mill_hours=30, finishing_line_hours=30),
            ohio, _config(max_cascade_depth=2),
        )
        assert r.simulation_depth <= 2

    def test_multiple_ohio_orders_no_impact(self):
        ohio = [
            _ohio_order(order_id=f"PO-2026-{i:03d}", due_days=90, position=i)
            for i in range(100, 105)
        ]
        r = simulate_cascade(
            _order(rolling_mill_hours=5, finishing_line_hours=5),
            ohio, _config(),
        )
        assert r.passed is True
        assert r.total_orders_impacted == 0


# ---------------------------------------------------------------------------
# Recommendation Derivation
# ---------------------------------------------------------------------------


def _l1(passed=True, failure_reason=None):
    from constraint_matching_agent.models.schemas import EquipmentCheckResult
    return EquipmentCheckResult(
        passed=passed, failure_reason=failure_reason,
        explanation="ok" if passed else (failure_reason or "fail"),
    )


def _l2(passed=True, match_status="Full Match", shortfall=0.0, lead=0):
    from constraint_matching_agent.models.schemas import MaterialCheckResult
    return MaterialCheckResult(
        passed=passed, match_status=match_status,
        required_tons=100, available_surplus_tons=100 - shortfall,
        shortfall_tons=shortfall, procurement_lead_time_days=lead,
        explanation="ok",
    )


def _l3(passed=True, escalation=False, tier="Normal", failure_reason=None):
    from constraint_matching_agent.models.schemas import UtilizationCheckResult
    return UtilizationCheckResult(
        passed=passed, shift_escalation_needed=escalation,
        recommended_shift_tier=tier,
        rolling_mill_available_hrs=100, rolling_mill_required_hrs=10,
        finishing_line_available_hrs=100, finishing_line_required_hrs=8,
        failure_reason=failure_reason, explanation="ok",
    )


def _l4(passed=True, failure_reason=None):
    from constraint_matching_agent.models.schemas import CascadeImpactResult
    return CascadeImpactResult(
        passed=passed, failure_reason=failure_reason, explanation="ok",
    )


class TestDeriveRecommendation:
    def test_all_pass_transfer(self):
        cat, _, conds = derive_recommendation(_l1(), _l2(), _l3(), _l4())
        assert cat == RecommendationCategory.TRANSFER
        assert conds == []

    def test_l1_fail_non_transferable(self):
        cat, expl, _ = derive_recommendation(
            _l1(passed=False, failure_reason="no RM"),
            _l2(), _l3(), _l4(),
        )
        assert cat == RecommendationCategory.NON_TRANSFERABLE
        assert "L1" in expl

    def test_l2_fail_non_transferable(self):
        cat, _, _ = derive_recommendation(
            _l1(),
            _l2(passed=False, match_status="No Match"),
            _l3(), _l4(),
        )
        assert cat == RecommendationCategory.NON_TRANSFERABLE

    def test_l4_fail_non_transferable(self):
        cat, _, _ = derive_recommendation(
            _l1(), _l2(), _l3(),
            _l4(passed=False, failure_reason="penalty"),
        )
        assert cat == RecommendationCategory.NON_TRANSFERABLE

    def test_partial_material_only(self):
        cat, _, conds = derive_recommendation(
            _l1(),
            _l2(match_status="Partial Match", shortfall=50, lead=5),
            _l3(), _l4(),
        )
        assert cat == RecommendationCategory.TRANSFER_WITH_PROCUREMENT
        assert len(conds) == 1
        assert "procurement" in conds[0].lower()

    def test_overtime_only(self):
        cat, _, conds = derive_recommendation(
            _l1(), _l2(),
            _l3(escalation=True, tier="Overtime"),
            _l4(),
        )
        assert cat == RecommendationCategory.TRANSFER_ON_OVERTIME
        assert len(conds) == 1

    def test_weekend_only(self):
        cat, _, conds = derive_recommendation(
            _l1(), _l2(),
            _l3(escalation=True, tier="Weekend"),
            _l4(),
        )
        assert cat == RecommendationCategory.TRANSFER_ON_WEEKEND

    def test_multiple_conditions(self):
        cat, _, conds = derive_recommendation(
            _l1(),
            _l2(match_status="Partial Match", shortfall=50, lead=5),
            _l3(escalation=True, tier="Overtime"),
            _l4(),
        )
        assert cat == RecommendationCategory.TRANSFER_WITH_CONDITIONS
        assert len(conds) == 2

    def test_multiple_failures(self):
        cat, expl, _ = derive_recommendation(
            _l1(passed=False, failure_reason="no RM"),
            _l2(passed=False, match_status="No Match"),
            _l3(passed=False, failure_reason="no hrs"),
            _l4(passed=False, failure_reason="penalty"),
        )
        assert cat == RecommendationCategory.NON_TRANSFERABLE
        assert "L1" in expl and "L2" in expl


# ---------------------------------------------------------------------------
# evaluate_funnel (integration of all layers)
# ---------------------------------------------------------------------------


class TestEvaluateFunnel:
    def test_all_pass(self):
        t = _tracker(material=500, workforce=100)
        r = evaluate_funnel(
            order=_order(),
            equipment=_equipment(gauge_min=1.0, gauge_max=5.0),
            materials={"procurement_lead_time_days": 5,
                       "net_available_hours_per_week": 40},
            workforce={"operators_per_rolling_mill": 1,
                      "operators_per_finishing_line": 1},
            ohio_orders=[],
            tracker=t,
            config=_config(),
        )
        assert r.all_layers_passed is True
        assert r.recommendation_category == RecommendationCategory.TRANSFER
        assert r.order_id == "PO-2026-001"
        assert r.priority == "P1"

    def test_equipment_fail(self):
        t = _tracker()
        r = evaluate_funnel(
            order=_order(product_family="Widgets"),
            equipment=_equipment(),
            materials={},
            workforce={"operators_per_rolling_mill": 1,
                      "operators_per_finishing_line": 1},
            ohio_orders=[],
            tracker=t,
            config=_config(),
        )
        assert r.all_layers_passed is False
        assert r.recommendation_category == RecommendationCategory.NON_TRANSFERABLE

    def test_material_partial_with_overtime(self):
        t = _tracker(material=50, rm_normal=5, rm_ot=20, workforce=100)
        due = (date.today() + timedelta(days=30)).isoformat()
        r = evaluate_funnel(
            order=_order(raw_material_tons=100, due_date=due,
                         rolling_mill_hours=10, finishing_line_hours=8),
            equipment=_equipment(),
            materials={"procurement_lead_time_days": 5,
                       "net_available_hours_per_week": 40},
            workforce={"operators_per_rolling_mill": 1,
                      "operators_per_finishing_line": 1},
            ohio_orders=[],
            tracker=t,
            config=_config(),
        )
        assert r.recommendation_category == RecommendationCategory.TRANSFER_WITH_CONDITIONS
        assert len(r.conditions) == 2

    def test_funnel_result_fields(self):
        t = _tracker()
        r = evaluate_funnel(
            order=_order(),
            equipment=_equipment(),
            materials={},
            workforce={"operators_per_rolling_mill": 1,
                      "operators_per_finishing_line": 1},
            ohio_orders=[],
            tracker=t,
            config=_config(),
        )
        assert r.layer1_equipment is not None
        assert r.layer2_material is not None
        assert r.layer3_utilization is not None
        assert r.layer4_cascade is not None
        assert r.recommendation != ""
        assert r.recommendation_explanation != ""
