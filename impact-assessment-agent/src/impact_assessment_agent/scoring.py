"""Pure Python priority scoring engine.

Deterministic — same input always produces same output.
No LLM calls. Registered as Strands Python tools so the
LLM can invoke scoring after fetching data via MCP tools.

Implements: BR-IA-01 through BR-IA-15.
"""

from __future__ import annotations

import logging
from datetime import date, datetime
from typing import Any

from impact_assessment_agent.models.schemas import (
    CriterionScores,
    OrderExplanation,
    PriorityGroupTable,
    PrioritySummary,
    PriorityThresholds,
    OrderTableRow,
    ScoredOrder,
    ScoringWeights,
)

logger = logging.getLogger("impact_assessment_agent")


# -------------------------------------------------------------------
# Individual criterion scoring functions
# -------------------------------------------------------------------

def compute_urgency_score(due_date_str: str) -> int:
    """Discrete bracket mapping for days-to-due-date (BR-IA-02).

    Returns 0-100 integer.
    """
    today = date.today()
    try:
        due = datetime.strptime(due_date_str, "%Y-%m-%d").date()
    except (ValueError, TypeError):
        logger.warning("Invalid due_date '%s', defaulting urgency=50", due_date_str)
        return 50

    days_remaining = (due - today).days

    if days_remaining <= 0:
        return 100
    if days_remaining <= 3:
        return 95
    if days_remaining <= 7:
        return 80
    if days_remaining <= 14:
        return 50
    if days_remaining <= 21:
        return 30
    if days_remaining <= 30:
        return 15
    return 5


def compute_tier_score(tier: str) -> int:
    """Fixed mapping for customer tier (BR-IA-02).

    Returns 0-100 integer.
    """
    mapping = {"Tier1": 100, "Tier2": 60, "Tier3": 25}
    return mapping.get(tier, 50)


def compute_value_score(
    order_value: float, min_val: float, max_val: float
) -> int:
    """Min-max normalization across order set (BR-IA-02, BR-IA-10).

    Returns 0-100 integer.
    """
    if max_val == min_val:
        return 50
    raw = ((order_value - min_val) / (max_val - min_val)) * 100
    return int(round(raw))


def compute_complexity_score(machine_types: list[str]) -> int:
    """Fixed mapping for machine complexity (BR-IA-15).

    Returns 0-100 integer.
    """
    if not machine_types:
        logger.warning("Empty machine_types_required, defaulting complexity=0")
        return 0
    has_rm = "Rolling Mill" in machine_types
    has_fl = "Finishing Line" in machine_types
    if has_rm and has_fl:
        return 100
    if has_rm:
        return 60
    if has_fl:
        return 40
    logger.warning("Unknown machine types %s, defaulting complexity=0", machine_types)
    return 0


# -------------------------------------------------------------------
# Classification
# -------------------------------------------------------------------

def classify(weighted_score: float, thresholds: PriorityThresholds) -> str:
    """Assign P1/P2/P3 based on score and thresholds (BR-IA-04)."""
    if weighted_score >= thresholds.p1:
        return "P1"
    if weighted_score >= thresholds.p2:
        return "P2"
    return "P3"


def _sort_key(order: ScoredOrder) -> tuple:
    """Sort key: priority group asc, score desc, due_date asc, order_id asc (BR-IA-07)."""
    priority_rank = {"P1": 0, "P2": 1, "P3": 2}
    return (
        priority_rank.get(order.priority, 3),
        -order.weighted_score,
        order.due_date,
        order.order_id,
    )


# -------------------------------------------------------------------
# Main scoring pipeline
# -------------------------------------------------------------------

def score_orders(
    orders: list[dict[str, Any]],
    customers: dict[str, dict[str, Any]],
    weights: ScoringWeights,
    thresholds: PriorityThresholds,
) -> list[ScoredOrder]:
    """Score and classify a list of orders (BR-IA-01 through BR-IA-11).

    Args:
        orders: Raw order dicts from ERP Data MCP get_orders response.
        customers: Dict keyed by customer_id from get_customers response.
        weights: Scoring weights.
        thresholds: Priority thresholds.

    Returns:
        Sorted list of ScoredOrder instances.
    """
    if not orders:
        return []

    values = [o.get("order_value", 0.0) for o in orders]
    min_val = min(values)
    max_val = max(values)

    scored: list[ScoredOrder] = []
    for o in orders:
        cust_id = o.get("customer_id", "")
        cust = customers.get(cust_id, {})
        cust_name = cust.get("customer_name", "Unknown")
        cust_tier = o.get("customer_tier", cust.get("customer_tier", "Tier3"))

        machine_types = o.get("machine_types_required", [])

        scores = CriterionScores(
            urgency=compute_urgency_score(o.get("due_date", "")),
            customer_tier=compute_tier_score(cust_tier),
            order_value=compute_value_score(o.get("order_value", 0.0), min_val, max_val),
            machine_complexity=compute_complexity_score(machine_types),
        )

        weighted = round(
            scores.urgency * weights.urgency
            + scores.customer_tier * weights.customer_tier
            + scores.order_value * weights.order_value
            + scores.machine_complexity * weights.machine_complexity,
            2,
        )

        priority = classify(weighted, thresholds)

        scored.append(
            ScoredOrder(
                order_id=o["order_id"],
                product_family=o.get("product_family", ""),
                customer_id=cust_id,
                customer_name=cust_name,
                customer_tier=cust_tier,
                due_date=o.get("due_date", ""),
                quantity=o.get("quantity", 0),
                order_value=o.get("order_value", 0.0),
                machine_types_required=machine_types,
                scores=scores,
                weighted_score=weighted,
                priority=priority,
                rolling_mill_hours=o.get("rolling_mill_hours", 0.0),
                finishing_line_hours=o.get("finishing_line_hours", 0.0),
                raw_material_tons=o.get("raw_material_tons", 0.0),
            )
        )

    scored.sort(key=_sort_key)
    return scored


# -------------------------------------------------------------------
# Reclassification (BR-IA-05, BR-IA-06)
# -------------------------------------------------------------------

def reclassify_order(
    scored_orders: list[ScoredOrder],
    order_id: str,
    new_priority: str,
    weights: ScoringWeights,
    thresholds: PriorityThresholds,
) -> tuple[ScoredOrder, list[ScoredOrder]]:
    """Pin one order and re-evaluate non-pinned orders.

    Returns:
        Tuple of (overridden_order, list_of_orders_whose_priority_changed).
    """
    overridden: ScoredOrder | None = None
    for o in scored_orders:
        if o.order_id == order_id:
            overridden = o.model_copy(
                update={
                    "original_priority": o.priority,
                    "priority": new_priority,
                    "manually_classified": True,
                }
            )
            break

    if overridden is None:
        raise ValueError(f"Order {order_id} not found in scored orders")

    # Re-evaluate non-pinned orders (BR-IA-06)
    changed: list[ScoredOrder] = []
    result: list[ScoredOrder] = []
    for o in scored_orders:
        if o.order_id == order_id:
            result.append(overridden)
            continue
        if o.manually_classified:
            result.append(o)
            continue
        new_p = classify(o.weighted_score, thresholds)
        if new_p != o.priority:
            updated = o.model_copy(update={"priority": new_p})
            changed.append(updated)
            result.append(updated)
        else:
            result.append(o)

    result.sort(key=_sort_key)
    return overridden, changed


# -------------------------------------------------------------------
# Summary and explanation helpers
# -------------------------------------------------------------------

def build_priority_summary(scored_orders: list[ScoredOrder]) -> PrioritySummary:
    """Build distribution summary from scored orders (US-02 Phase 1)."""
    p1 = [o for o in scored_orders if o.priority == "P1"]
    p2 = [o for o in scored_orders if o.priority == "P2"]
    p3 = [o for o in scored_orders if o.priority == "P3"]

    # Determine primary driver: criterion with highest avg contribution
    if scored_orders:
        avg_urg = sum(o.scores.urgency for o in scored_orders) / len(scored_orders)
        avg_tier = sum(o.scores.customer_tier for o in scored_orders) / len(scored_orders)
        avg_val = sum(o.scores.order_value for o in scored_orders) / len(scored_orders)
        avg_cx = sum(o.scores.machine_complexity for o in scored_orders) / len(scored_orders)
        drivers = {
            "urgency": avg_urg,
            "customer_tier": avg_tier,
            "order_value": avg_val,
            "machine_complexity": avg_cx,
        }
        primary_driver = max(drivers, key=drivers.get)  # type: ignore[arg-type]
    else:
        primary_driver = "none"

    p1_val = sum(o.order_value for o in p1)
    p2_val = sum(o.order_value for o in p2)
    p3_val = sum(o.order_value for o in p3)
    total = len(scored_orders)

    summary_text = (
        f"Analyzed {total} Florida orders. "
        f"P1 (Must Move): {len(p1)} orders (${p1_val:,.0f}). "
        f"P2 (Move if Capacity): {len(p2)} orders (${p2_val:,.0f}). "
        f"P3 (Defer): {len(p3)} orders (${p3_val:,.0f}). "
        f"Primary driver: {primary_driver}."
    )

    return PrioritySummary(
        total_orders=total,
        p1_count=len(p1),
        p2_count=len(p2),
        p3_count=len(p3),
        p1_total_value=p1_val,
        p2_total_value=p2_val,
        p3_total_value=p3_val,
        primary_driver=primary_driver,
        summary_text=summary_text,
    )


def build_explanation(order: ScoredOrder, weights: ScoringWeights) -> OrderExplanation:
    """Build per-order classification explanation (US-02 Phase 3)."""
    s = order.scores
    text = (
        f"Order {order.order_id} scored {order.weighted_score:.1f}/100 ({order.priority}):\n"
        f"  Urgency: {s.urgency}/100 (weight {weights.urgency})\n"
        f"  Customer Tier: {s.customer_tier}/100 ({order.customer_tier}, weight {weights.customer_tier})\n"
        f"  Order Value: {s.order_value}/100 (${order.order_value:,.0f}, weight {weights.order_value})\n"
        f"  Machine Complexity: {s.machine_complexity}/100 (weight {weights.machine_complexity})\n"
        f"  Weighted: {weights.urgency}*{s.urgency} + {weights.customer_tier}*{s.customer_tier}"
        f" + {weights.order_value}*{s.order_value} + {weights.machine_complexity}*{s.machine_complexity}"
        f" = {order.weighted_score:.1f}"
    )
    return OrderExplanation(
        order_id=order.order_id,
        weighted_score=order.weighted_score,
        priority=order.priority,
        scores=order.scores,
        weights_used=weights,
        explanation_text=text,
    )


def build_group_tables(
    scored_orders: list[ScoredOrder],
) -> list[PriorityGroupTable]:
    """Build grouped tables for P1/P2/P3 (US-02 Phase 2)."""
    tables: list[PriorityGroupTable] = []
    for p in ("P1", "P2", "P3"):
        group = [o for o in scored_orders if o.priority == p]
        rows = [
            OrderTableRow(
                order_id=o.order_id,
                product_family=o.product_family,
                customer_name=o.customer_name,
                customer_tier=o.customer_tier,
                due_date=o.due_date,
                quantity=o.quantity,
                order_value=o.order_value,
                weighted_score=o.weighted_score,
            )
            for o in group
        ]
        tables.append(
            PriorityGroupTable(
                priority=p,
                orders=rows,
                subtotal_quantity=sum(o.quantity for o in group),
                subtotal_value=sum(o.order_value for o in group),
            )
        )
    return tables
