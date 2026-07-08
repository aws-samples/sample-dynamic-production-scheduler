"""Unit tests for Pydantic schema models."""

import pytest
from pydantic import ValidationError

from capacity_optimization_agent.models.schemas import (
    BottleneckInfo,
    CapacityAgentConfig,
    CapacityAuditEntry,
    CapacitySnapshot,
    ConstraintImpact,
    ConstraintInput,
    DelayCandidateInfo,
    DelayDecision,
    DelayDecisionInput,
    DelayResult,
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


# ---------------------------------------------------------------------------
# CapacityAgentConfig
# ---------------------------------------------------------------------------

class TestCapacityAgentConfig:
    def test_defaults(self):
        c = CapacityAgentConfig()
        assert c.rerouting_window_days == 10
        assert c.delay_threshold_days == 42
        assert c.utilization_warning_pct == 0.90

    def test_custom_values(self):
        c = CapacityAgentConfig(
            rerouting_window_days=15,
            delay_threshold_days=30,
            utilization_warning_pct=0.85,
        )
        assert c.rerouting_window_days == 15

    def test_zero_window_rejected(self):
        with pytest.raises(ValidationError):
            CapacityAgentConfig(rerouting_window_days=0)

    def test_utilization_above_one_rejected(self):
        with pytest.raises(ValidationError):
            CapacityAgentConfig(utilization_warning_pct=1.5)


# ---------------------------------------------------------------------------
# EquipmentCapability
# ---------------------------------------------------------------------------

class TestEquipmentCapability:
    def test_valid_equipment(self):
        e = EquipmentCapability(
            machine_type="Rolling Mill",
            product_families_supported=["Hot-Rolled Coil"],
            total_hours_per_week=120.0,
            planned_downtime_hrs_week=8.0,
            net_available_hours_per_week=112.0,
            gauge_range_min=0.5,
            gauge_range_max=25.0,
            setup_time_by_family={"Hot-Rolled Coil": 2.0},
        )
        assert e.net_available_hours_per_week == 112.0

    def test_optional_gauge_fields(self):
        e = EquipmentCapability(
            machine_type="Finishing Line",
            total_hours_per_week=100.0,
            net_available_hours_per_week=95.0,
        )
        assert e.gauge_range_min is None
        assert e.gauge_range_max is None

    def test_negative_hours_rejected(self):
        with pytest.raises(ValidationError):
            EquipmentCapability(
                machine_type="X",
                total_hours_per_week=-10.0,
                net_available_hours_per_week=5.0,
            )


# ---------------------------------------------------------------------------
# ShiftUtilization
# ---------------------------------------------------------------------------

class TestShiftUtilization:
    def test_valid_shift(self):
        s = ShiftUtilization(
            shift_type="Normal",
            total_hours=80.0,
            committed_hours=60.0,
            surplus_hours=20.0,
            utilization_pct=75.0,
        )
        assert s.surplus_hours == 20.0

    def test_invalid_shift_type_rejected(self):
        with pytest.raises(ValidationError):
            ShiftUtilization(
                shift_type="Night",
                total_hours=40.0,
            )

    def test_utilization_above_100_rejected(self):
        with pytest.raises(ValidationError):
            ShiftUtilization(
                shift_type="Normal",
                total_hours=80.0,
                utilization_pct=101.0,
            )


# ---------------------------------------------------------------------------
# MachineUtilization
# ---------------------------------------------------------------------------

class TestMachineUtilization:
    def _make_shift(self, shift_type, total=80.0, committed=0.0):
        return ShiftUtilization(
            shift_type=shift_type,
            total_hours=total,
            committed_hours=committed,
            surplus_hours=total - committed,
            utilization_pct=(committed / total * 100) if total else 0.0,
        )

    def test_valid_machine_utilization(self):
        m = MachineUtilization(
            machine_type="Rolling Mill",
            normal=self._make_shift("Normal", 80, 60),
            overtime=self._make_shift("Overtime", 40, 0),
            weekend=self._make_shift("Weekend", 20, 0),
            total_surplus_hours=80.0,
            effective_surplus_hours=20.0,
        )
        assert m.effective_surplus_hours == 20.0


# ---------------------------------------------------------------------------
# WorkforceAvailability
# ---------------------------------------------------------------------------

class TestWorkforceAvailability:
    def test_valid_workforce(self):
        m = WorkforceAvailability(
            total_operators=25,
            currently_allocated=17,
            available_surplus=8,
        )
        assert m.available_surplus == 8

    def test_negative_operators_rejected(self):
        with pytest.raises(ValidationError):
            WorkforceAvailability(total_operators=-1)


# ---------------------------------------------------------------------------
# MaterialSurplus
# ---------------------------------------------------------------------------

class TestMaterialSurplus:
    def test_valid_material(self):
        m = MaterialSurplus(
            material_type="HR Slab",
            current_inventory_tons=500.0,
            committed_to_orders_tons=350.0,
            available_surplus_tons=150.0,
        )
        assert m.available_surplus_tons == 150.0


# ---------------------------------------------------------------------------
# OhioOrderLoad
# ---------------------------------------------------------------------------

class TestOhioOrderLoad:
    def test_valid_order(self):
        o = OhioOrderLoad(
            order_id="PO-2026-015",
            product_family="Hot-Rolled Coil",
            customer_id="CUST-0003",
            customer_tier="Tier2",
            due_date="2026-06-15",
            quantity=300,
            order_value=95000.0,
            priority="P3",
            slack_days=55,
        )
        assert o.slack_days == 55

    def test_invalid_order_id_rejected(self):
        with pytest.raises(ValidationError):
            OhioOrderLoad(
                order_id="INVALID",
                product_family="X",
                customer_id="C1",
                customer_tier="Tier1",
                due_date="2026-01-01",
                quantity=1,
                order_value=1.0,
            )

    def test_invalid_tier_rejected(self):
        with pytest.raises(ValidationError):
            OhioOrderLoad(
                order_id="PO-2026-001",
                product_family="X",
                customer_id="C1",
                customer_tier="Gold",
                due_date="2026-01-01",
                quantity=1,
                order_value=1.0,
            )


# ---------------------------------------------------------------------------
# SurplusSummary & BottleneckInfo
# ---------------------------------------------------------------------------

class TestSurplusSummary:
    def test_defaults(self):
        s = SurplusSummary()
        assert s.rolling_mill_normal_hrs == 0.0
        assert s.total_workforce_surplus == 0

    def test_custom_values(self):
        s = SurplusSummary(
            rolling_mill_normal_hrs=20.0,
            rolling_mill_overtime_hrs=15.0,
            finishing_line_normal_hrs=80.0,
            total_material_surplus_tons=150.0,
            total_workforce_surplus=8,
        )
        assert s.total_material_surplus_tons == 150.0


class TestBottleneckInfo:
    def test_valid_bottleneck(self):
        b = BottleneckInfo(
            machine_type="Rolling Mill",
            surplus_to_demand_ratio=0.32,
            surplus_hours=45.0,
            demand_hours=140.0,
            explanation="Rolling Mill is the constraint",
        )
        assert b.surplus_to_demand_ratio == 0.32


# ---------------------------------------------------------------------------
# CapacitySnapshot
# ---------------------------------------------------------------------------

class TestCapacitySnapshot:
    def test_minimal_snapshot(self):
        s = CapacitySnapshot(
            session_id="sess-001",
            analyzed_at="2026-03-17T10:00:00Z",
        )
        assert s.session_id == "sess-001"
        assert s.equipment == []


# ---------------------------------------------------------------------------
# DelayCandidateInfo
# ---------------------------------------------------------------------------

class TestDelayCandidateInfo:
    def test_valid_candidate(self):
        d = DelayCandidateInfo(
            order_id="PO-2026-015",
            product_family="Hot-Rolled Coil",
            customer_id="CUST-0003",
            customer_tier="Tier2",
            due_date="2026-06-15",
            quantity=300,
            order_value=95000.0,
            slack_days=55,
            freed_rolling_mill_hours=30.0,
            freed_finishing_line_hours=15.0,
            freed_material_tons=25.0,
            freed_operator_hours=12.0,
            remaining_buffer_days=13,
            risk_level="Medium",
            trade_off_explanation="Frees 30 RM hours",
        )
        assert d.risk_level == "Medium"

    def test_invalid_risk_level_rejected(self):
        with pytest.raises(ValidationError):
            DelayCandidateInfo(
                order_id="PO-2026-015",
                product_family="X",
                customer_id="C1",
                customer_tier="Tier1",
                due_date="2026-01-01",
                quantity=1,
                order_value=1.0,
                risk_level="Critical",
            )


# ---------------------------------------------------------------------------
# DelayDecision & DelayResult
# ---------------------------------------------------------------------------

class TestDelayDecision:
    def test_valid_decision(self):
        d = DelayDecision(
            order_id="PO-2026-015",
            approved=True,
            decided_at="2026-03-17T10:30:00Z",
        )
        assert d.approved is True

    def test_invalid_order_id(self):
        with pytest.raises(ValidationError):
            DelayDecision(order_id="BAD", approved=False)


class TestDelayResult:
    def test_empty_result(self):
        r = DelayResult()
        assert r.decisions == []


# ---------------------------------------------------------------------------
# PlannerConstraint & ConstraintImpact
# ---------------------------------------------------------------------------

class TestPlannerConstraint:
    def test_valid_constraint(self):
        c = PlannerConstraint(
            constraint_text="No weekend shifts",
            constraint_type="shift_restriction",
            applied_at="2026-03-17T11:00:00Z",
            impact_description="Weekend hours zeroed",
        )
        assert c.constraint_type == "shift_restriction"

    def test_empty_text_rejected(self):
        with pytest.raises(ValidationError):
            PlannerConstraint(
                constraint_text="",
                constraint_type="other",
            )

    def test_invalid_type_rejected(self):
        with pytest.raises(ValidationError):
            PlannerConstraint(
                constraint_text="Some constraint",
                constraint_type="invalid_type",
            )

    def test_text_too_long_rejected(self):
        with pytest.raises(ValidationError):
            PlannerConstraint(
                constraint_text="x" * 501,
                constraint_type="other",
            )


class TestConstraintImpact:
    def test_valid_impact(self):
        ci = ConstraintImpact(
            constraint=PlannerConstraint(
                constraint_text="No overtime",
                constraint_type="shift_restriction",
            ),
        )
        assert ci.constraint.constraint_type == "shift_restriction"


# ---------------------------------------------------------------------------
# Input Validation Schemas
# ---------------------------------------------------------------------------

class TestDelayDecisionInput:
    def test_valid_approve(self):
        d = DelayDecisionInput(order_id="PO-2026-015", action="approve")
        assert d.action == "approve"

    def test_valid_reject(self):
        d = DelayDecisionInput(order_id="PO-2026-015", action="reject")
        assert d.action == "reject"

    def test_invalid_action_rejected(self):
        with pytest.raises(ValidationError):
            DelayDecisionInput(order_id="PO-2026-015", action="delay")

    def test_invalid_order_id_rejected(self):
        with pytest.raises(ValidationError):
            DelayDecisionInput(order_id="BAD", action="approve")


class TestConstraintInput:
    def test_valid_input(self):
        c = ConstraintInput(
            constraint_text="No weekend shifts",
            constraint_type="shift_restriction",
        )
        assert c.constraint_type == "shift_restriction"

    def test_empty_text_rejected(self):
        with pytest.raises(ValidationError):
            ConstraintInput(constraint_text="", constraint_type="other")

    def test_invalid_type_rejected(self):
        with pytest.raises(ValidationError):
            ConstraintInput(
                constraint_text="Something",
                constraint_type="bad_type",
            )


# ---------------------------------------------------------------------------
# CapacityAuditEntry
# ---------------------------------------------------------------------------

class TestCapacityAuditEntry:
    def test_valid_entry(self):
        e = CapacityAuditEntry(
            session_id="sess-001",
            action="capacity_analysis",
            timestamp="2026-03-17T10:00:00Z",
            details={"bottleneck": "Rolling Mill"},
        )
        assert e.action == "capacity_analysis"

    def test_delay_decision_action(self):
        e = CapacityAuditEntry(
            session_id="sess-001",
            action="delay_decision",
            timestamp="2026-03-17T10:30:00Z",
            details={"order_id": "PO-2026-015", "approved": True},
        )
        assert e.action == "delay_decision"

    def test_invalid_action_rejected(self):
        with pytest.raises(ValidationError):
            CapacityAuditEntry(
                session_id="sess-001",
                action="invalid_action",
                timestamp="2026-03-17T10:00:00Z",
                details={},
            )


# ---------------------------------------------------------------------------
# SharedCapacitySnapshot
# ---------------------------------------------------------------------------

class TestSharedCapacitySnapshot:
    def test_valid_shared_snapshot(self):
        s = SharedCapacitySnapshot(
            session_id="sess-001",
            analyzed_at="2026-03-17T10:00:00Z",
            rerouting_window_days=10,
            delays_approved=["PO-2026-015", "PO-2026-018"],
        )
        assert len(s.delays_approved) == 2

    def test_defaults(self):
        s = SharedCapacitySnapshot(
            session_id="sess-001",
            analyzed_at="2026-03-17T10:00:00Z",
        )
        assert s.active_constraints == []
        assert s.delays_approved == []
