"""Unit tests for Pydantic schema models."""

import pytest
from pydantic import ValidationError

from impact_assessment_agent.models.schemas import (
    ClassificationAuditEntry,
    CriterionScores,
    OrderExplanation,
    OrderTableRow,
    PriorityGroupTable,
    PrioritySummary,
    PriorityThresholds,
    ReclassifyInput,
    ScoredOrder,
    ScoringWeights,
    SharedOrderEntry,
    SharedPrioritizedOrders,
)


# ---------------------------------------------------------------------------
# ScoringWeights
# ---------------------------------------------------------------------------

class TestScoringWeights:
    def test_default_weights_valid(self):
        w = ScoringWeights()
        assert w.urgency == 0.40
        assert w.customer_tier == 0.25
        assert w.order_value == 0.20
        assert w.machine_complexity == 0.15

    def test_custom_weights_sum_to_one(self):
        w = ScoringWeights(
            urgency=0.50, customer_tier=0.20,
            order_value=0.20, machine_complexity=0.10,
        )
        assert w.urgency == 0.50

    def test_weights_not_summing_to_one_rejected(self):
        with pytest.raises(ValidationError, match="sum to 1.0"):
            ScoringWeights(
                urgency=0.50, customer_tier=0.50,
                order_value=0.50, machine_complexity=0.50,
            )

    def test_negative_weight_rejected(self):
        with pytest.raises(ValidationError):
            ScoringWeights(
                urgency=-0.10, customer_tier=0.40,
                order_value=0.40, machine_complexity=0.30,
            )

    def test_zero_weight_allowed(self):
        w = ScoringWeights(
            urgency=0.0, customer_tier=0.50,
            order_value=0.30, machine_complexity=0.20,
        )
        assert w.urgency == 0.0


# ---------------------------------------------------------------------------
# PriorityThresholds
# ---------------------------------------------------------------------------

class TestPriorityThresholds:
    def test_default_thresholds_valid(self):
        t = PriorityThresholds()
        assert t.p1 == 75
        assert t.p2 == 50

    def test_custom_thresholds_valid(self):
        t = PriorityThresholds(p1=80, p2=40)
        assert t.p1 == 80

    def test_p1_must_exceed_p2(self):
        with pytest.raises(ValidationError, match="must be >"):
            PriorityThresholds(p1=50, p2=50)

    def test_p1_less_than_p2_rejected(self):
        with pytest.raises(ValidationError):
            PriorityThresholds(p1=30, p2=60)

    def test_threshold_out_of_range(self):
        with pytest.raises(ValidationError):
            PriorityThresholds(p1=100, p2=50)


# ---------------------------------------------------------------------------
# CriterionScores
# ---------------------------------------------------------------------------

class TestCriterionScores:
    def test_valid_scores(self):
        s = CriterionScores(
            urgency=95, customer_tier=100,
            order_value=65, machine_complexity=60,
        )
        assert s.urgency == 95

    def test_score_above_100_rejected(self):
        with pytest.raises(ValidationError):
            CriterionScores(
                urgency=101, customer_tier=50,
                order_value=50, machine_complexity=50,
            )

    def test_negative_score_rejected(self):
        with pytest.raises(ValidationError):
            CriterionScores(
                urgency=-1, customer_tier=50,
                order_value=50, machine_complexity=50,
            )


# ---------------------------------------------------------------------------
# ScoredOrder
# ---------------------------------------------------------------------------

class TestScoredOrder:
    def test_valid_scored_order(self):
        o = ScoredOrder(
            order_id="PO-2026-001",
            product_family="Hot-Rolled Coil",
            customer_id="CUST-0001",
            customer_name="Acme Manufacturing",
            customer_tier="Tier1",
            due_date="2026-03-20",
            quantity=500,
            order_value=180000.0,
            machine_types_required=["Rolling Mill", "Finishing Line"],
            scores=CriterionScores(
                urgency=95, customer_tier=100,
                order_value=65, machine_complexity=100,
            ),
            weighted_score=91.0,
            priority="P1",
            rolling_mill_hours=12.0,
            finishing_line_hours=8.0,
            raw_material_tons=50.0,
        )
        assert o.priority == "P1"

    def test_invalid_order_id_rejected(self):
        with pytest.raises(ValidationError):
            ScoredOrder(
                order_id="INVALID",
                product_family="X",
                customer_id="C1",
                customer_name="C",
                customer_tier="Tier1",
                due_date="2026-03-20",
                quantity=1,
                order_value=1.0,
                machine_types_required=[],
                scores=CriterionScores(
                    urgency=50, customer_tier=50,
                    order_value=50, machine_complexity=50,
                ),
                weighted_score=50.0,
                priority="P2",
            )

    def test_invalid_priority_rejected(self):
        with pytest.raises(ValidationError):
            ScoredOrder(
                order_id="PO-2026-001",
                product_family="X",
                customer_id="C1",
                customer_name="C",
                customer_tier="Tier1",
                due_date="2026-03-20",
                quantity=1,
                order_value=1.0,
                machine_types_required=[],
                scores=CriterionScores(
                    urgency=50, customer_tier=50,
                    order_value=50, machine_complexity=50,
                ),
                weighted_score=50.0,
                priority="P4",
            )


# ---------------------------------------------------------------------------
# ReclassifyInput
# ---------------------------------------------------------------------------

class TestReclassifyInput:
    def test_valid_input(self):
        r = ReclassifyInput(order_id="PO-2026-003", new_priority="P1")
        assert r.new_priority == "P1"

    def test_invalid_order_id(self):
        with pytest.raises(ValidationError):
            ReclassifyInput(order_id="BAD", new_priority="P1")

    def test_invalid_priority(self):
        with pytest.raises(ValidationError):
            ReclassifyInput(order_id="PO-2026-003", new_priority="P0")


# ---------------------------------------------------------------------------
# ClassificationAuditEntry
# ---------------------------------------------------------------------------

class TestClassificationAuditEntry:
    def test_valid_classification_entry(self):
        e = ClassificationAuditEntry(
            session_id="abc-123",
            action="priority_classification",
            timestamp="2026-03-16T10:00:00Z",
            details={"total_orders": 20, "p1_count": 8},
        )
        assert e.action == "priority_classification"

    def test_invalid_action_rejected(self):
        with pytest.raises(ValidationError):
            ClassificationAuditEntry(
                session_id="abc-123",
                action="invalid_action",
                timestamp="2026-03-16T10:00:00Z",
                details={},
            )


# ---------------------------------------------------------------------------
# PrioritySummary
# ---------------------------------------------------------------------------

class TestPrioritySummary:
    def test_valid_summary(self):
        s = PrioritySummary(
            total_orders=20, p1_count=8, p2_count=7, p3_count=5,
            p1_total_value=2400000.0, p2_total_value=1100000.0,
            p3_total_value=400000.0,
            primary_driver="urgency",
            summary_text="8 P1, 7 P2, 5 P3",
        )
        assert s.total_orders == 20
