"""Unit tests for the scoring engine."""

from __future__ import annotations

from datetime import date, timedelta

import pytest

from impact_assessment_agent.models.schemas import (
    PriorityThresholds,
    ScoringWeights,
)
from impact_assessment_agent.scoring import (
    build_explanation,
    build_group_tables,
    build_priority_summary,
    classify,
    compute_complexity_score,
    compute_tier_score,
    compute_urgency_score,
    compute_value_score,
    reclassify_order,
    score_orders,
)


# -------------------------------------------------------------------
# Urgency scoring
# -------------------------------------------------------------------

class TestComputeUrgencyScore:
    def test_overdue(self):
        yesterday = (date.today() - timedelta(days=1)).isoformat()
        assert compute_urgency_score(yesterday) == 100

    def test_due_today(self):
        assert compute_urgency_score(date.today().isoformat()) == 100

    def test_due_in_2_days(self):
        d = (date.today() + timedelta(days=2)).isoformat()
        assert compute_urgency_score(d) == 95

    def test_due_in_5_days(self):
        d = (date.today() + timedelta(days=5)).isoformat()
        assert compute_urgency_score(d) == 80

    def test_due_in_10_days(self):
        d = (date.today() + timedelta(days=10)).isoformat()
        assert compute_urgency_score(d) == 50

    def test_due_in_18_days(self):
        d = (date.today() + timedelta(days=18)).isoformat()
        assert compute_urgency_score(d) == 30

    def test_due_in_25_days(self):
        d = (date.today() + timedelta(days=25)).isoformat()
        assert compute_urgency_score(d) == 15

    def test_due_in_60_days(self):
        d = (date.today() + timedelta(days=60)).isoformat()
        assert compute_urgency_score(d) == 5

    def test_invalid_date_defaults_50(self):
        assert compute_urgency_score("not-a-date") == 50


# -------------------------------------------------------------------
# Tier scoring
# -------------------------------------------------------------------

class TestComputeTierScore:
    def test_tier1(self):
        assert compute_tier_score("Tier1") == 100

    def test_tier2(self):
        assert compute_tier_score("Tier2") == 60

    def test_tier3(self):
        assert compute_tier_score("Tier3") == 25

    def test_unknown_tier_defaults_50(self):
        assert compute_tier_score("Unknown") == 50


# -------------------------------------------------------------------
# Value scoring
# -------------------------------------------------------------------

class TestComputeValueScore:
    def test_min_value_gets_zero(self):
        assert compute_value_score(100.0, 100.0, 500.0) == 0

    def test_max_value_gets_100(self):
        assert compute_value_score(500.0, 100.0, 500.0) == 100

    def test_mid_value(self):
        assert compute_value_score(300.0, 100.0, 500.0) == 50

    def test_all_same_value_gets_50(self):
        assert compute_value_score(200.0, 200.0, 200.0) == 50


# -------------------------------------------------------------------
# Complexity scoring
# -------------------------------------------------------------------

class TestComputeComplexityScore:
    def test_both_machines(self):
        assert compute_complexity_score(["Rolling Mill", "Finishing Line"]) == 100

    def test_rolling_mill_only(self):
        assert compute_complexity_score(["Rolling Mill"]) == 60

    def test_finishing_line_only(self):
        assert compute_complexity_score(["Finishing Line"]) == 40

    def test_empty_list(self):
        assert compute_complexity_score([]) == 0

    def test_unknown_machine(self):
        assert compute_complexity_score(["Laser Cutter"]) == 0


# -------------------------------------------------------------------
# Classification
# -------------------------------------------------------------------

class TestClassify:
    def test_p1(self):
        t = PriorityThresholds(p1=75, p2=50)
        assert classify(80.0, t) == "P1"

    def test_p1_boundary(self):
        t = PriorityThresholds(p1=75, p2=50)
        assert classify(75.0, t) == "P1"

    def test_p2(self):
        t = PriorityThresholds(p1=75, p2=50)
        assert classify(60.0, t) == "P2"

    def test_p2_boundary(self):
        t = PriorityThresholds(p1=75, p2=50)
        assert classify(50.0, t) == "P2"

    def test_p3(self):
        t = PriorityThresholds(p1=75, p2=50)
        assert classify(30.0, t) == "P3"


# -------------------------------------------------------------------
# Fixtures
# -------------------------------------------------------------------

def _make_order(
    order_id: str = "PO-2026-001",
    due_days: int = 2,
    tier: str = "Tier1",
    value: float = 180000.0,
    machines: list[str] | None = None,
) -> dict:
    d = (date.today() + timedelta(days=due_days)).isoformat()
    return {
        "order_id": order_id,
        "plant": "Florida",
        "product_family": "Hot-Rolled Coil",
        "quantity": 500,
        "due_date": d,
        "machine_types_required": machines or ["Rolling Mill", "Finishing Line"],
        "customer_id": "CUST-0001",
        "order_value": value,
        "customer_tier": tier,
        "priority": None,
        "status": "Active",
        "rolling_mill_hours": 12.0,
        "finishing_line_hours": 8.0,
        "raw_material_tons": 50.0,
    }


CUSTOMERS = {
    "CUST-0001": {
        "customer_id": "CUST-0001",
        "customer_name": "Acme Manufacturing",
        "customer_tier": "Tier1",
    },
    "CUST-0002": {
        "customer_id": "CUST-0002",
        "customer_name": "Beta Corp",
        "customer_tier": "Tier3",
    },
}

DEFAULT_WEIGHTS = ScoringWeights()
DEFAULT_THRESHOLDS = PriorityThresholds()


# -------------------------------------------------------------------
# score_orders integration
# -------------------------------------------------------------------

class TestScoreOrders:
    def test_empty_list(self):
        assert score_orders([], {}, DEFAULT_WEIGHTS, DEFAULT_THRESHOLDS) == []

    def test_single_order_classified(self):
        orders = [_make_order()]
        result = score_orders(orders, CUSTOMERS, DEFAULT_WEIGHTS, DEFAULT_THRESHOLDS)
        assert len(result) == 1
        assert result[0].priority in ("P1", "P2", "P3")
        assert result[0].order_id == "PO-2026-001"

    def test_sort_order_p1_before_p2(self):
        orders = [
            _make_order("PO-2026-001", due_days=2, tier="Tier1", value=200000.0),
            _make_order("PO-2026-002", due_days=60, tier="Tier3", value=10000.0,
                        machines=["Finishing Line"]),
        ]
        result = score_orders(orders, CUSTOMERS, DEFAULT_WEIGHTS, DEFAULT_THRESHOLDS)
        assert len(result) == 2
        # First order should have higher priority
        priorities = [r.priority for r in result]
        assert priorities[0] <= priorities[1] or result[0].weighted_score >= result[1].weighted_score

    def test_all_same_value_gets_50_value_score(self):
        orders = [
            _make_order("PO-2026-001", value=100000.0),
            _make_order("PO-2026-002", value=100000.0),
        ]
        result = score_orders(orders, CUSTOMERS, DEFAULT_WEIGHTS, DEFAULT_THRESHOLDS)
        for r in result:
            assert r.scores.order_value == 50


# -------------------------------------------------------------------
# Reclassification
# -------------------------------------------------------------------

class TestReclassifyOrder:
    def test_reclassify_pins_order(self):
        orders = [_make_order("PO-2026-001"), _make_order("PO-2026-002", due_days=60)]
        scored = score_orders(orders, CUSTOMERS, DEFAULT_WEIGHTS, DEFAULT_THRESHOLDS)
        overridden, changed = reclassify_order(
            scored, "PO-2026-002", "P1", DEFAULT_WEIGHTS, DEFAULT_THRESHOLDS,
        )
        assert overridden.priority == "P1"
        assert overridden.manually_classified is True
        assert overridden.original_priority is not None

    def test_reclassify_unknown_order_raises(self):
        orders = [_make_order()]
        scored = score_orders(orders, CUSTOMERS, DEFAULT_WEIGHTS, DEFAULT_THRESHOLDS)
        with pytest.raises(ValueError, match="not found"):
            reclassify_order(scored, "PO-9999-999", "P1", DEFAULT_WEIGHTS, DEFAULT_THRESHOLDS)


# -------------------------------------------------------------------
# Summary and explanation
# -------------------------------------------------------------------

class TestBuildPrioritySummary:
    def test_summary_counts(self):
        orders = [
            _make_order("PO-2026-001", due_days=2, value=200000.0),
            _make_order("PO-2026-002", due_days=60, tier="Tier3", value=10000.0,
                        machines=["Finishing Line"]),
        ]
        scored = score_orders(orders, CUSTOMERS, DEFAULT_WEIGHTS, DEFAULT_THRESHOLDS)
        summary = build_priority_summary(scored)
        assert summary.total_orders == 2
        assert summary.p1_count + summary.p2_count + summary.p3_count == 2
        assert summary.primary_driver in (
            "urgency", "customer_tier", "order_value", "machine_complexity",
        )


class TestBuildExplanation:
    def test_explanation_text(self):
        orders = [_make_order()]
        scored = score_orders(orders, CUSTOMERS, DEFAULT_WEIGHTS, DEFAULT_THRESHOLDS)
        exp = build_explanation(scored[0], DEFAULT_WEIGHTS)
        assert scored[0].order_id in exp.explanation_text
        assert exp.priority == scored[0].priority


class TestBuildGroupTables:
    def test_three_groups_returned(self):
        orders = [_make_order()]
        scored = score_orders(orders, CUSTOMERS, DEFAULT_WEIGHTS, DEFAULT_THRESHOLDS)
        tables = build_group_tables(scored)
        assert len(tables) == 3
        priorities = {t.priority for t in tables}
        assert priorities == {"P1", "P2", "P3"}
