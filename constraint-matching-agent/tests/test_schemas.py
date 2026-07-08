"""Unit tests for Constraint Matching Agent Pydantic schemas."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from constraint_matching_agent.models.schemas import (
    AgentConfig,
    CapacityConsumed,
    CascadeImpactedOrder,
    CascadeImpactResult,
    ConstraintMatchingAuditEntry,
    EquipmentCheckResult,
    FunnelResult,
    MaterialCheckResult,
    OrderDecision,
    OrderDecisionInput,
    OrderDecisionResult,
    ProcessedOrderEntry,
    RecommendationCategory,
    RevisitInput,
    RunningCapacityTracker,
    RunningShiftHours,
    ShiftEscalationOption,
    SkipQueueEntry,
    TransferSummary,
    UtilizationCheckResult,
)


# ---------------------------------------------------------------------------
# AgentConfig
# ---------------------------------------------------------------------------


class TestAgentConfig:
    def test_defaults(self):
        cfg = AgentConfig()
        assert cfg.utilization_warning_pct == 0.90
        assert cfg.max_cascade_depth == 5
        assert cfg.cascade_timeout_secs == 3
        assert cfg.checkpoint_interval_secs == 300

    def test_custom_values(self):
        cfg = AgentConfig(
            utilization_warning_pct=0.85,
            max_cascade_depth=3,
            cascade_timeout_secs=5,
            checkpoint_interval_secs=600,
        )
        assert cfg.utilization_warning_pct == 0.85
        assert cfg.max_cascade_depth == 3

    def test_warning_pct_out_of_range(self):
        with pytest.raises(ValidationError):
            AgentConfig(utilization_warning_pct=1.5)

    def test_cascade_depth_zero(self):
        with pytest.raises(ValidationError):
            AgentConfig(max_cascade_depth=0)


# ---------------------------------------------------------------------------
# RecommendationCategory
# ---------------------------------------------------------------------------


class TestRecommendationCategory:
    def test_all_values(self):
        assert RecommendationCategory.TRANSFER == "Transfer"
        assert RecommendationCategory.NON_TRANSFERABLE == "Non-transferable"
        assert RecommendationCategory.TRANSFER_ON_OVERTIME == "Transfer on overtime"
        assert RecommendationCategory.TRANSFER_ON_WEEKEND == "Transfer on weekend"
        assert RecommendationCategory.TRANSFER_WITH_PROCUREMENT == "Transfer with procurement"
        assert RecommendationCategory.TRANSFER_WITH_CONDITIONS == "Transfer with conditions"


# ---------------------------------------------------------------------------
# Layer Result Models
# ---------------------------------------------------------------------------


class TestEquipmentCheckResult:
    def test_pass(self):
        r = EquipmentCheckResult(passed=True, explanation="All compatible")
        assert r.passed is True
        assert r.gauge_in_range is True

    def test_fail_with_reason(self):
        r = EquipmentCheckResult(
            passed=False,
            rolling_mill_compatible=False,
            failure_reason="Steel Bars not supported",
            explanation="Fail",
        )
        assert r.passed is False
        assert r.rolling_mill_compatible is False


class TestMaterialCheckResult:
    def test_full_match(self):
        r = MaterialCheckResult(
            passed=True,
            match_status="Full Match",
            required_tons=100.0,
            available_surplus_tons=120.0,
        )
        assert r.match_status == "Full Match"

    def test_invalid_match_status(self):
        with pytest.raises(ValidationError):
            MaterialCheckResult(
                passed=False,
                match_status="Unknown",
                required_tons=10.0,
            )

    def test_partial_match(self):
        r = MaterialCheckResult(
            passed=True,
            match_status="Partial Match",
            required_tons=100.0,
            available_surplus_tons=60.0,
            shortfall_tons=40.0,
            procurement_feasible=True,
        )
        assert r.procurement_feasible is True
        assert r.shortfall_tons == 40.0


class TestShiftEscalationOption:
    def test_valid(self):
        opt = ShiftEscalationOption(
            shift_tier="Overtime",
            rolling_mill_surplus_hrs=10.0,
            finishing_line_surplus_hrs=8.0,
        )
        assert opt.shift_tier == "Overtime"

    def test_invalid_tier(self):
        with pytest.raises(ValidationError):
            ShiftEscalationOption(shift_tier="Night")


class TestUtilizationCheckResult:
    def test_normal_pass(self):
        r = UtilizationCheckResult(
            passed=True,
            rolling_mill_available_hrs=40.0,
            rolling_mill_required_hrs=20.0,
            finishing_line_available_hrs=30.0,
            finishing_line_required_hrs=15.0,
            workforce_available=10,
            workforce_required=5,
        )
        assert r.passed is True
        assert r.shift_escalation_needed is False

    def test_invalid_shift_tier(self):
        with pytest.raises(ValidationError):
            UtilizationCheckResult(
                passed=True,
                recommended_shift_tier="Night",
            )


class TestCascadeImpactedOrder:
    def test_valid(self):
        o = CascadeImpactedOrder(
            order_id="PO-2026-001",
            original_slack_days=5,
            new_slack_days=-2,
            days_past_deadline=2,
            penalty_clause=True,
            cascade_level=1,
        )
        assert o.days_past_deadline == 2

    def test_invalid_order_id(self):
        with pytest.raises(ValidationError):
            CascadeImpactedOrder(order_id="INVALID")


class TestCascadeImpactResult:
    def test_pass_no_impact(self):
        r = CascadeImpactResult(passed=True, simulation_depth=3)
        assert r.total_orders_impacted == 0
        assert r.has_penalty_risk is False

    def test_fail_with_penalty(self):
        r = CascadeImpactResult(
            passed=False,
            simulation_depth=2,
            total_orders_impacted=1,
            has_penalty_risk=True,
            failure_reason="Penalty risk",
        )
        assert r.has_penalty_risk is True


# ---------------------------------------------------------------------------
# FunnelResult
# ---------------------------------------------------------------------------


class TestFunnelResult:
    def _make_layers(self):
        l1 = EquipmentCheckResult(passed=True, explanation="OK")
        l2 = MaterialCheckResult(
            passed=True, match_status="Full Match", required_tons=50.0
        )
        l3 = UtilizationCheckResult(passed=True)
        l4 = CascadeImpactResult(passed=True, simulation_depth=3)
        return l1, l2, l3, l4

    def test_all_pass(self):
        l1, l2, l3, l4 = self._make_layers()
        fr = FunnelResult(
            order_id="PO-2026-001",
            priority="P1",
            layer1_equipment=l1,
            layer2_material=l2,
            layer3_utilization=l3,
            layer4_cascade=l4,
            all_layers_passed=True,
            recommendation_category=RecommendationCategory.TRANSFER,
        )
        assert fr.all_layers_passed is True

    def test_invalid_priority(self):
        l1, l2, l3, l4 = self._make_layers()
        with pytest.raises(ValidationError):
            FunnelResult(
                order_id="PO-2026-001",
                priority="P4",
                layer1_equipment=l1,
                layer2_material=l2,
                layer3_utilization=l3,
                layer4_cascade=l4,
            )


# ---------------------------------------------------------------------------
# Running Capacity Tracker
# ---------------------------------------------------------------------------


class TestRunningShiftHours:
    def test_defaults(self):
        h = RunningShiftHours()
        assert h.normal_hrs == 0.0
        assert h.total_hrs == 0.0

    def test_negative_rejected(self):
        with pytest.raises(ValidationError):
            RunningShiftHours(normal_hrs=-1.0)


class TestProcessedOrderEntry:
    def test_approved(self):
        e = ProcessedOrderEntry(
            order_id="PO-2026-005",
            decision="approved",
            rolling_mill_hrs_consumed=10.0,
        )
        assert e.decision == "approved"

    def test_invalid_decision(self):
        with pytest.raises(ValidationError):
            ProcessedOrderEntry(
                order_id="PO-2026-005",
                decision="cancelled",
            )


class TestRunningCapacityTracker:
    def test_minimal(self):
        t = RunningCapacityTracker(session_id="sess-001")
        assert t.material_remaining_tons == 0.0
        assert t.orders_approved == []

    def test_with_orders(self):
        t = RunningCapacityTracker(
            session_id="sess-001",
            orders_approved=["PO-2026-001"],
            orders_rejected=["PO-2026-002"],
        )
        assert len(t.orders_approved) == 1


# ---------------------------------------------------------------------------
# Planner Decision Models
# ---------------------------------------------------------------------------


class TestCapacityConsumed:
    def test_valid(self):
        c = CapacityConsumed(
            rolling_mill_hrs=10.0,
            finishing_line_hrs=8.0,
            material_tons=50.0,
            operator_hrs=20.0,
            shift_tier_used="Overtime",
        )
        assert c.shift_tier_used == "Overtime"

    def test_invalid_tier(self):
        with pytest.raises(ValidationError):
            CapacityConsumed(shift_tier_used="Night")


class TestOrderDecision:
    def test_approve(self):
        d = OrderDecision(order_id="PO-2026-003", action="approve")
        assert d.action == "approve"

    def test_invalid_action(self):
        with pytest.raises(ValidationError):
            OrderDecision(order_id="PO-2026-003", action="cancel")

    def test_invalid_order_id(self):
        with pytest.raises(ValidationError):
            OrderDecision(order_id="BAD", action="approve")


class TestOrderDecisionResult:
    def test_with_capacity(self):
        r = OrderDecisionResult(
            order_id="PO-2026-003",
            action="approve",
            capacity_consumed=CapacityConsumed(rolling_mill_hrs=5.0),
            tracker_updated=True,
        )
        assert r.tracker_updated is True
        assert r.capacity_consumed.rolling_mill_hrs == 5.0

    def test_reject_no_capacity(self):
        r = OrderDecisionResult(
            order_id="PO-2026-003",
            action="reject",
        )
        assert r.capacity_consumed is None


# ---------------------------------------------------------------------------
# Input Validation & Skip Queue
# ---------------------------------------------------------------------------


class TestOrderDecisionInput:
    def test_valid(self):
        i = OrderDecisionInput(order_id="PO-2026-001", action="skip")
        assert i.reason == ""

    def test_reason_max_length(self):
        i = OrderDecisionInput(
            order_id="PO-2026-001", action="reject", reason="x" * 500
        )
        assert len(i.reason) == 500

    def test_reason_too_long(self):
        with pytest.raises(ValidationError):
            OrderDecisionInput(
                order_id="PO-2026-001", action="reject", reason="x" * 501
            )


class TestRevisitInput:
    def test_valid(self):
        r = RevisitInput(order_id="PO-2026-010")
        assert r.order_id == "PO-2026-010"

    def test_invalid(self):
        with pytest.raises(ValidationError):
            RevisitInput(order_id="INVALID-ID")


class TestSkipQueueEntry:
    def test_valid(self):
        e = SkipQueueEntry(
            order_id="PO-2026-007",
            priority="P2",
            original_position=3,
        )
        assert e.revisit_requested is False


# ---------------------------------------------------------------------------
# Transfer Summary & Audit
# ---------------------------------------------------------------------------


class TestTransferSummary:
    def test_defaults(self):
        s = TransferSummary()
        assert s.total_orders_evaluated == 0

    def test_populated(self):
        s = TransferSummary(
            total_orders_evaluated=10,
            orders_approved=6,
            orders_rejected=2,
            orders_skipped=2,
            total_rm_hrs_consumed=50.0,
            total_fl_hrs_consumed=40.0,
            total_material_consumed=200.0,
        )
        assert s.orders_approved + s.orders_rejected + s.orders_skipped == 10


class TestConstraintMatchingAuditEntry:
    def test_funnel_evaluation(self):
        e = ConstraintMatchingAuditEntry(
            session_id="sess-001",
            action="funnel_evaluation",
            timestamp="2026-03-17T10:00:00Z",
            details={"order_id": "PO-2026-001", "passed": True},
        )
        assert e.agent == "constraint_matching_agent"

    def test_invalid_action(self):
        with pytest.raises(ValidationError):
            ConstraintMatchingAuditEntry(
                session_id="sess-001",
                action="invalid_action",
                timestamp="2026-03-17T10:00:00Z",
                details={},
            )
