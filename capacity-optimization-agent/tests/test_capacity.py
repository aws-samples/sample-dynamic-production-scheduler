"""Unit tests for the capacity engine (BR-CO-01 through BR-CO-18)."""

import pytest
from datetime import date, timedelta

from capacity_optimization_agent.models.schemas import (
    BottleneckInfo,
    CapacitySnapshot,
    ConstraintImpact,
    DelayCandidateInfo,
    EquipmentCapability,
    MachineUtilization,
    WorkforceAvailability,
    MaterialSurplus,
    OhioOrderLoad,
    PlannerConstraint,
    SharedCapacitySnapshot,
    ShiftUtilization,
    SurplusSummary,
)
from capacity_optimization_agent.capacity import (
    CapacityState,
    build_delay_result,
    build_shared_snapshot,
    build_surplus_summary,
    check_utilization_warnings,
    compute_machine_utilization,
    compute_shift_utilization,
    compute_slack_days,
    enrich_orders,
    filter_delay_candidates,
    identify_bottleneck,
)


# -------------------------------------------------------------------
# Helpers
# -------------------------------------------------------------------

def _make_mu(machine_type, normal_total, normal_committed, ot_total, wk_total):
    """Build a MachineUtilization for testing."""
    return compute_machine_utilization(
        machine_type, normal_total, normal_committed, ot_total, wk_total,
    )


def _future(days: int) -> str:
    return (date.today() + timedelta(days=days)).strftime("%Y-%m-%d")


# -------------------------------------------------------------------
# ShiftUtilization (BR-CO-03)
# -------------------------------------------------------------------

class TestComputeShiftUtilization:
    def test_normal_shift(self):
        s = compute_shift_utilization(80.0, 60.0, "Normal")
        assert s.surplus_hours == 20.0
        assert s.utilization_pct == 75.0

    def test_zero_total_hours(self):
        s = compute_shift_utilization(0.0, 0.0, "Normal")
        assert s.utilization_pct == 0.0
        assert s.surplus_hours == 0.0

    def test_over_committed(self):
        s = compute_shift_utilization(80.0, 100.0, "Normal")
        assert s.surplus_hours == 0.0  # clamped to 0

    def test_overtime_no_committed(self):
        s = compute_shift_utilization(40.0, 0.0, "Overtime")
        assert s.surplus_hours == 40.0
        assert s.utilization_pct == 0.0


# -------------------------------------------------------------------
# MachineUtilization (BR-CO-03)
# -------------------------------------------------------------------

class TestComputeMachineUtilization:
    def test_tiered_surplus(self):
        mu = _make_mu("Rolling Mill", 80.0, 60.0, 40.0, 20.0)
        assert mu.normal.surplus_hours == 20.0
        assert mu.overtime.surplus_hours == 40.0
        assert mu.weekend.surplus_hours == 20.0
        assert mu.total_surplus_hours == 80.0
        # Effective = normal only
        assert mu.effective_surplus_hours == 20.0


# -------------------------------------------------------------------
# Bottleneck Identification (BR-CO-04)
# -------------------------------------------------------------------

class TestIdentifyBottleneck:
    def test_rolling_mill_bottleneck(self):
        rm = _make_mu("Rolling Mill", 80, 60, 0, 0)   # 20 surplus
        fl = _make_mu("Finishing Line", 100, 20, 0, 0)  # 80 surplus
        demand = {"Rolling Mill": 140.0, "Finishing Line": 100.0}
        b = identify_bottleneck([rm, fl], demand)
        assert b.machine_type == "Rolling Mill"
        assert b.surplus_to_demand_ratio < 1.0

    def test_zero_demand_is_not_bottleneck(self):
        rm = _make_mu("Rolling Mill", 80, 60, 0, 0)
        fl = _make_mu("Finishing Line", 100, 20, 0, 0)
        demand = {"Rolling Mill": 140.0, "Finishing Line": 0.0}
        b = identify_bottleneck([rm, fl], demand)
        assert b.machine_type == "Rolling Mill"

    def test_equal_ratio_tiebreaker_rolling_mill(self):
        rm = _make_mu("Rolling Mill", 100, 50, 0, 0)   # 50 surplus
        fl = _make_mu("Finishing Line", 100, 50, 0, 0)  # 50 surplus
        demand = {"Rolling Mill": 100.0, "Finishing Line": 100.0}
        b = identify_bottleneck([rm, fl], demand)
        assert b.machine_type == "Rolling Mill"

    def test_empty_utilization(self):
        b = identify_bottleneck([], {})
        assert b.machine_type == "Unknown"


# -------------------------------------------------------------------
# Surplus Summary
# -------------------------------------------------------------------

class TestBuildSurplusSummary:
    def test_basic_summary(self):
        rm = _make_mu("Rolling Mill", 80, 60, 15, 10)
        fl = _make_mu("Finishing Line", 100, 20, 35, 25)
        mats = [
            MaterialSurplus(
                material_type="HR Slab",
                current_inventory_tons=500,
                committed_to_orders_tons=350,
                available_surplus_tons=150,
            )
        ]
        mp = WorkforceAvailability(
            total_operators=25, currently_allocated=17, available_surplus=8,
        )
        s = build_surplus_summary([rm, fl], mats, mp)
        assert s.rolling_mill_normal_hrs == 20.0
        assert s.finishing_line_normal_hrs == 80.0
        assert s.total_material_surplus_tons == 150.0
        assert s.total_workforce_surplus == 8

    def test_no_workforce(self):
        s = build_surplus_summary([], [], None)
        assert s.total_workforce_surplus == 0


# -------------------------------------------------------------------
# Slack Calculation (BR-CO-17)
# -------------------------------------------------------------------

class TestComputeSlackDays:
    def test_future_order_positive_slack(self):
        due = _future(30)
        slack = compute_slack_days(due, 10.0, 8.0, 8.0)
        # 30 days - (10/8 = 1.25 days) ~ 28
        assert slack > 0

    def test_past_due_negative_slack(self):
        due = (date.today() - timedelta(days=5)).strftime("%Y-%m-%d")
        slack = compute_slack_days(due, 8.0, 8.0, 8.0)
        assert slack < 0

    def test_invalid_date_returns_zero(self):
        assert compute_slack_days("bad-date", 8.0, 8.0, 8.0) == 0

    def test_zero_daily_hours(self):
        due = _future(30)
        slack = compute_slack_days(due, 10.0, 8.0, 0.0)
        assert slack == 30


# -------------------------------------------------------------------
# Order Enrichment (BR-CO-06, BR-CO-17)
# -------------------------------------------------------------------

class TestEnrichOrders:
    def test_basic_enrichment(self):
        raw = [{
            "order_id": "PO-2026-015",
            "product_family": "Hot-Rolled Coil",
            "customer_id": "CUST-0003",
            "customer_tier": "Tier2",
            "due_date": _future(60),
            "quantity": 300,
            "order_value": 95000.0,
            "rolling_mill_hours": 12.0,
            "finishing_line_hours": 8.0,
            "raw_material_tons": 25.0,
            "priority": "P3",
        }]
        customers = {
            "CUST-0003": {"customer_name": "Test Co", "penalty_clause": False},
        }
        equipment = [EquipmentCapability(
            machine_type="Rolling Mill",
            total_hours_per_week=120,
            net_available_hours_per_week=112,
        )]
        orders = enrich_orders(raw, customers, equipment)
        assert len(orders) == 1
        assert orders[0].order_id == "PO-2026-015"
        assert orders[0].slack_days > 0
        assert orders[0].penalty_clause is False


# -------------------------------------------------------------------
# Delay Candidate Filtering (BR-CO-06, BR-CO-07, BR-CO-08, BR-CO-09)
# -------------------------------------------------------------------

class TestFilterDelayCandidates:
    def _make_order(self, order_id, priority, slack, penalty=False, rm_hrs=10.0, fl_hrs=5.0):
        return OhioOrderLoad(
            order_id=order_id,
            product_family="Hot-Rolled Coil",
            customer_id="CUST-0001",
            customer_tier="Tier2",
            due_date=_future(slack + 42),
            quantity=100,
            order_value=50000.0,
            priority=priority,
            rolling_mill_hours=rm_hrs,
            finishing_line_hours=fl_hrs,
            raw_material_tons=10.0,
            slack_days=slack,
            penalty_clause=penalty,
        )

    def test_p3_with_sufficient_slack(self):
        orders = [self._make_order("PO-2026-015", "P3", 55)]
        mp = WorkforceAvailability(
            total_operators=25, currently_allocated=17, available_surplus=8,
            operators_per_rolling_mill=2, operators_per_finishing_line=1,
        )
        candidates = filter_delay_candidates(orders, 42, mp, "Rolling Mill")
        assert len(candidates) == 1
        assert candidates[0].risk_level == "Medium"  # 55-42=13 buffer

    def test_p1_excluded(self):
        orders = [self._make_order("PO-2026-001", "P1", 55)]
        candidates = filter_delay_candidates(orders, 42, None, "Rolling Mill")
        assert len(candidates) == 0

    def test_penalty_excluded(self):
        orders = [self._make_order("PO-2026-015", "P3", 55, penalty=True)]
        candidates = filter_delay_candidates(orders, 42, None, "Rolling Mill")
        assert len(candidates) == 0

    def test_insufficient_slack_excluded(self):
        orders = [self._make_order("PO-2026-015", "P3", 30)]
        candidates = filter_delay_candidates(orders, 42, None, "Rolling Mill")
        assert len(candidates) == 0

    def test_risk_levels(self):
        orders = [
            self._make_order("PO-2026-015", "P3", 70),  # 70-42=28 -> Low
            self._make_order("PO-2026-016", "P3", 55),  # 55-42=13 -> Medium
            self._make_order("PO-2026-017", "P3", 48),  # 48-42=6  -> High
        ]
        candidates = filter_delay_candidates(orders, 42, None, "Rolling Mill")
        risks = {c.order_id: c.risk_level for c in candidates}
        assert risks["PO-2026-015"] == "Low"
        assert risks["PO-2026-016"] == "Medium"
        assert risks["PO-2026-017"] == "High"

    def test_sort_by_freed_bottleneck_hours(self):
        orders = [
            self._make_order("PO-2026-015", "P3", 55, rm_hrs=10.0),
            self._make_order("PO-2026-016", "P3", 55, rm_hrs=30.0),
        ]
        candidates = filter_delay_candidates(orders, 42, None, "Rolling Mill")
        assert candidates[0].order_id == "PO-2026-016"  # 30 hrs first

    def test_null_priority_included(self):
        orders = [self._make_order("PO-2026-015", None, 55)]
        candidates = filter_delay_candidates(orders, 42, None, "Rolling Mill")
        assert len(candidates) == 1


# -------------------------------------------------------------------
# CapacityState — Cached Snapshot (Pattern 8, BR-CO-10, BR-CO-11)
# -------------------------------------------------------------------

class TestCapacityState:
    def _make_snapshot(self):
        rm = _make_mu("Rolling Mill", 80, 60, 40, 20)
        fl = _make_mu("Finishing Line", 100, 20, 35, 25)
        mp = WorkforceAvailability(
            total_operators=25, currently_allocated=17, available_surplus=8,
        )
        mats = [MaterialSurplus(
            material_type="HR Slab",
            current_inventory_tons=500,
            committed_to_orders_tons=350,
            available_surplus_tons=150,
        )]
        summary = build_surplus_summary([rm, fl], mats, mp)
        demand = {"Rolling Mill": 140.0, "Finishing Line": 100.0}
        bottleneck = identify_bottleneck([rm, fl], demand)
        return CapacitySnapshot(
            session_id="sess-001",
            analyzed_at="2026-03-17T10:00:00Z",
            utilization=[rm, fl],
            workforce=mp,
            materials=mats,
            total_surplus_summary=summary,
            bottleneck=bottleneck,
        )

    def test_apply_delay_increases_surplus(self):
        snap = self._make_snapshot()
        state = CapacityState(snap)
        before_rm = state.snapshot.total_surplus_summary.rolling_mill_normal_hrs
        demand = {"Rolling Mill": 140.0, "Finishing Line": 100.0}
        state.apply_delay("PO-2026-015", 10.0, 5.0, 5.0, 2, demand)
        after_rm = state.snapshot.total_surplus_summary.rolling_mill_normal_hrs
        assert after_rm > before_rm

    def test_apply_constraint_shift_restriction(self):
        snap = self._make_snapshot()
        state = CapacityState(snap)
        demand = {"Rolling Mill": 140.0, "Finishing Line": 100.0}
        constraint = PlannerConstraint(
            constraint_text="No weekend shifts",
            constraint_type="shift_restriction",
        )
        impact = state.apply_constraint(constraint, demand)
        # Weekend surplus should be zeroed
        for mu in state.snapshot.utilization:
            assert mu.weekend.total_hours == 0.0
            assert mu.weekend.surplus_hours == 0.0
        assert "No weekend shifts" in state.snapshot.active_constraints

    def test_apply_constraint_capacity_limit(self):
        snap = self._make_snapshot()
        state = CapacityState(snap)
        demand = {"Rolling Mill": 140.0, "Finishing Line": 100.0}
        constraint = PlannerConstraint(
            constraint_text="Cap Rolling Mill at 80%",
            constraint_type="capacity_limit",
        )
        impact = state.apply_constraint(constraint, demand)
        assert impact.capacity_after is not None


# -------------------------------------------------------------------
# Utilization Warnings (BR-CO-05)
# -------------------------------------------------------------------

class TestCheckUtilizationWarnings:
    def test_warning_triggered(self):
        mu = _make_mu("Rolling Mill", 100, 95, 0, 0)  # 95% utilization
        warnings = check_utilization_warnings([mu], 0.90)
        assert len(warnings) == 1
        assert "Rolling Mill" in warnings[0]

    def test_no_warning_below_threshold(self):
        mu = _make_mu("Rolling Mill", 100, 50, 0, 0)  # 50% utilization
        warnings = check_utilization_warnings([mu], 0.90)
        assert len(warnings) == 0


# -------------------------------------------------------------------
# Shared Snapshot Builder (BR-CO-18)
# -------------------------------------------------------------------

class TestBuildSharedSnapshot:
    def test_basic_shared_snapshot(self):
        snap = CapacitySnapshot(
            session_id="sess-001",
            analyzed_at="2026-03-17T10:00:00Z",
            rerouting_window_days=10,
            bottleneck=BottleneckInfo(
                machine_type="Rolling Mill",
                surplus_to_demand_ratio=0.32,
                surplus_hours=45,
                demand_hours=140,
            ),
            total_surplus_summary=SurplusSummary(
                rolling_mill_normal_hrs=20,
                total_workforce_surplus=8,
            ),
            active_constraints=["No weekend shifts"],
        )
        shared = build_shared_snapshot(snap, ["PO-2026-015"])
        assert shared.session_id == "sess-001"
        assert len(shared.delays_approved) == 1
        assert shared.active_constraints == ["No weekend shifts"]
