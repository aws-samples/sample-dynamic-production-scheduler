"""Pure Python 4-layer constraint funnel engine.

Deterministic — same input + same tracker state = same output.
No LLM calls. Registered as Strands Python tools so the LLM can
invoke calculations after fetching data via MCP tools.

Implements: BR-CM-02 through BR-CM-08, BR-CM-16, BR-CM-17.
"""

from __future__ import annotations

import logging
import time
from datetime import date, datetime

from constraint_matching_agent.models.schemas import (
    AgentConfig,
    CascadeImpactedOrder,
    CascadeImpactResult,
    EquipmentCheckResult,
    FunnelResult,
    MaterialCheckResult,
    RecommendationCategory,
    RunningCapacityTracker,
    ShiftEscalationOption,
    UtilizationCheckResult,
)

logger = logging.getLogger("constraint_matching_agent")


# -------------------------------------------------------------------
# Layer 1: Equipment Compatibility (BR-CM-03, BR-CM-17)
# -------------------------------------------------------------------


def check_equipment_compatibility(
    order: dict,
    equipment: list[dict],
) -> EquipmentCheckResult:
    """Check product family support and gauge range."""
    product_family = order.get("product_family", "")
    gauge = order.get("gauge")

    rm_compatible = True
    fl_compatible = True
    gauge_in_range = True
    gauge_min = None
    gauge_max = None
    failure_reason = None
    explanation_parts: list[str] = []

    for eq in equipment:
        machine_type = eq.get("machine_type", "")
        families = eq.get("product_families_supported", [])

        if machine_type == "Rolling Mill":
            if product_family not in families:
                rm_compatible = False
                failure_reason = (
                    f"{product_family} not supported by Rolling Mill"
                )
            # Gauge check (BR-CM-17)
            gauge_min = eq.get("gauge_range_min")
            gauge_max = eq.get("gauge_range_max")
            if (
                gauge is not None
                and gauge_min is not None
                and gauge_max is not None
            ):
                if gauge < gauge_min or gauge > gauge_max:
                    gauge_in_range = False
                    failure_reason = (
                        f"Gauge {gauge}mm outside range "
                        f"[{gauge_min}-{gauge_max}mm]"
                    )
                else:
                    explanation_parts.append(
                        f"gauge {gauge}mm within range "
                        f"[{gauge_min}-{gauge_max}mm]"
                    )

        elif machine_type == "Finishing Line":
            if product_family not in families:
                fl_compatible = False
                failure_reason = (
                    f"{product_family} not supported by Finishing Line"
                )

    passed = rm_compatible and fl_compatible and gauge_in_range

    if passed:
        explanation = (
            f"Rolling Mill and Finishing Line support {product_family}"
        )
        if explanation_parts:
            explanation += ", " + ", ".join(explanation_parts)
    else:
        explanation = failure_reason or "Equipment incompatible"

    return EquipmentCheckResult(
        passed=passed,
        rolling_mill_compatible=rm_compatible,
        finishing_line_compatible=fl_compatible,
        gauge_in_range=gauge_in_range,
        gauge_order=gauge,
        gauge_machine_min=gauge_min,
        gauge_machine_max=gauge_max,
        failure_reason=failure_reason if not passed else None,
        explanation=explanation,
    )


# -------------------------------------------------------------------
# Layer 2: Material Availability (BR-CM-04)
# -------------------------------------------------------------------


def check_material_availability(
    order: dict,
    materials: dict,
    tracker: RunningCapacityTracker,
) -> MaterialCheckResult:
    """Check material surplus and procurement feasibility."""
    required = order.get("raw_material_tons", 0.0)
    available = tracker.material_remaining_tons

    procurement_lead = materials.get("procurement_lead_time_days", 0)
    net_hrs_week = materials.get("net_available_hours_per_week", 40.0)
    daily_hrs = net_hrs_week / 5.0 if net_hrs_week > 0 else 8.0

    rm_hrs = order.get("rolling_mill_hours", 0.0)
    fl_hrs = order.get("finishing_line_hours", 0.0)
    production_days = max(rm_hrs, fl_hrs) / daily_hrs if daily_hrs > 0 else 0.0

    due_date_str = order.get("due_date", "")
    try:
        due = datetime.strptime(due_date_str, "%Y-%m-%d").date()
        days_until_due = (due - date.today()).days
    except (ValueError, TypeError):
        days_until_due = 0

    if available >= required:
        return MaterialCheckResult(
            passed=True,
            match_status="Full Match",
            required_tons=required,
            available_surplus_tons=available,
            shortfall_tons=0.0,
            days_until_due_date=days_until_due,
            production_time_days=round(production_days, 1),
            explanation=(
                f"Full material match: {available:.0f} tons available "
                f">= {required:.0f} tons required"
            ),
        )

    shortfall = required - available
    total_lead = procurement_lead + production_days
    feasible = total_lead <= days_until_due

    if feasible:
        return MaterialCheckResult(
            passed=True,
            match_status="Partial Match",
            required_tons=required,
            available_surplus_tons=available,
            shortfall_tons=round(shortfall, 2),
            procurement_lead_time_days=procurement_lead,
            production_time_days=round(production_days, 1),
            days_until_due_date=days_until_due,
            procurement_feasible=True,
            explanation=(
                f"{available:.0f} of {required:.0f} tons available, "
                f"procurement feasible ({procurement_lead}d lead + "
                f"{production_days:.0f}d production = "
                f"{total_lead:.0f}d < {days_until_due}d to deadline)"
            ),
        )

    return MaterialCheckResult(
        passed=False,
        match_status="No Match",
        required_tons=required,
        available_surplus_tons=available,
        shortfall_tons=round(shortfall, 2),
        procurement_lead_time_days=procurement_lead,
        production_time_days=round(production_days, 1),
        days_until_due_date=days_until_due,
        procurement_feasible=False,
        failure_reason=(
            f"Procurement ({procurement_lead}d) + production "
            f"({production_days:.0f}d) = {total_lead:.0f}d exceeds "
            f"{days_until_due}d to deadline"
        ),
        explanation=(
            f"Material shortfall: {shortfall:.0f} tons, "
            f"procurement + production exceeds deadline"
        ),
    )


# -------------------------------------------------------------------
# Layer 3: Machine Utilization + Workforce (BR-CM-05, BR-CM-06)
# -------------------------------------------------------------------


def check_utilization_and_workforce(
    order: dict,
    tracker: RunningCapacityTracker,
    workforce: dict,
    config: AgentConfig,
) -> UtilizationCheckResult:
    """Check machine hours availability and workforce constraints."""
    rm_required = order.get("rolling_mill_hours", 0.0)
    fl_required = order.get("finishing_line_hours", 0.0)

    rm_hrs = tracker.rolling_mill_remaining_hrs
    fl_hrs = tracker.finishing_line_remaining_hrs

    rm_normal = rm_hrs.normal_hrs
    rm_ot = rm_hrs.overtime_hrs
    rm_wk = rm_hrs.weekend_hrs

    fl_normal = fl_hrs.normal_hrs
    fl_ot = fl_hrs.overtime_hrs
    fl_wk = fl_hrs.weekend_hrs

    # Determine recommended tier for each machine
    rm_tier = _determine_tier(rm_required, rm_normal, rm_ot, rm_wk)
    fl_tier = _determine_tier(fl_required, fl_normal, fl_ot, fl_wk)

    # Overall tier is the highest escalation needed
    tier_order = {"Normal": 0, "Overtime": 1, "Weekend": 2, "Insufficient": 3}
    overall_tier = rm_tier if tier_order.get(rm_tier, 3) >= tier_order.get(fl_tier, 3) else fl_tier

    escalation_needed = overall_tier != "Normal"
    passed = overall_tier != "Insufficient"
    failure_reason = None

    if not passed:
        failure_reason = (
            "Insufficient machine hours across all shifts"
        )

    # Build escalation options
    escalation_options: list[ShiftEscalationOption] = []
    if escalation_needed and passed:
        if overall_tier in ("Overtime", "Weekend"):
            escalation_options.append(ShiftEscalationOption(
                shift_tier="Overtime",
                rolling_mill_surplus_hrs=rm_ot,
                finishing_line_surplus_hrs=fl_ot,
            ))
        if overall_tier == "Weekend":
            escalation_options.append(ShiftEscalationOption(
                shift_tier="Weekend",
                rolling_mill_surplus_hrs=rm_wk,
                finishing_line_surplus_hrs=fl_wk,
            ))

    # Workforce check (BR-CM-06)
    ops_per_rm = workforce.get("operators_per_rolling_mill", 1)
    ops_per_fl = workforce.get("operators_per_finishing_line", 1)
    mp_required = int(rm_required * ops_per_rm + fl_required * ops_per_fl)
    mp_available = tracker.workforce_remaining
    mp_sufficient = mp_available >= mp_required

    # Tiered workforce constraint
    if overall_tier == "Normal":
        mp_constraint_type = "hard"
        if not mp_sufficient and passed:
            passed = False
            failure_reason = "Insufficient operators for normal shift"
    else:
        mp_constraint_type = "soft"

    # Utilization warning (BR-CM-05)
    rm_total_cap = rm_hrs.total_hrs + rm_required
    fl_total_cap = fl_hrs.total_hrs + fl_required
    rm_committed = rm_total_cap - rm_hrs.total_hrs + rm_required
    fl_committed = fl_total_cap - fl_hrs.total_hrs + fl_required
    util_warning = False
    if rm_total_cap > 0:
        rm_pct = rm_required / (rm_hrs.total_hrs + rm_required) if (rm_hrs.total_hrs + rm_required) > 0 else 0
        # Simpler: check if remaining after transfer < (1 - warning_pct) * original
        original_total = rm_hrs.total_hrs
        if original_total > 0:
            post_pct = 1.0 - ((original_total - rm_required) / original_total)
            if post_pct > config.utilization_warning_pct:
                util_warning = True
    if fl_hrs.total_hrs > 0:
        post_pct_fl = 1.0 - ((fl_hrs.total_hrs - fl_required) / fl_hrs.total_hrs)
        if post_pct_fl > config.utilization_warning_pct:
            util_warning = True

    # Explanation
    if passed and not escalation_needed:
        explanation = (
            f"Normal shift sufficient: RM {rm_normal:.0f}hrs avail "
            f">= {rm_required:.0f}hrs, FL {fl_normal:.0f}hrs avail "
            f">= {fl_required:.0f}hrs"
        )
    elif passed:
        explanation = (
            f"Requires {overall_tier} shift: RM needs {rm_required:.0f}hrs, "
            f"FL needs {fl_required:.0f}hrs"
        )
    else:
        explanation = failure_reason or "Utilization check failed"

    if not mp_sufficient and mp_constraint_type == "soft":
        explanation += ". Workforce: soft warning — temp workers may be needed"

    return UtilizationCheckResult(
        passed=passed,
        rolling_mill_available_hrs=rm_hrs.total_hrs,
        rolling_mill_required_hrs=rm_required,
        finishing_line_available_hrs=fl_hrs.total_hrs,
        finishing_line_required_hrs=fl_required,
        recommended_shift_tier=overall_tier if passed else "Normal",
        shift_escalation_needed=escalation_needed,
        escalation_options=escalation_options,
        utilization_warning=util_warning,
        workforce_sufficient=mp_sufficient,
        workforce_available=mp_available,
        workforce_required=mp_required,
        workforce_constraint_type=mp_constraint_type,
        failure_reason=failure_reason if not passed else None,
        explanation=explanation,
    )


def _determine_tier(
    required: float,
    normal: float,
    overtime: float,
    weekend: float,
) -> str:
    """Determine minimum shift tier needed for required hours."""
    if normal >= required:
        return "Normal"
    if normal + overtime >= required:
        return "Overtime"
    if normal + overtime + weekend >= required:
        return "Weekend"
    return "Insufficient"


# -------------------------------------------------------------------
# Layer 4: Cascade Impact Simulation (BR-CM-07, BR-CM-16)
# -------------------------------------------------------------------


def simulate_cascade(
    florida_order: dict,
    ohio_orders: list[dict],
    config: AgentConfig,
) -> CascadeImpactResult:
    """Simulate adding Florida order to Ohio schedule.

    Multi-level cascade with configurable timeout (Pattern 9).
    """
    if not ohio_orders:
        return CascadeImpactResult(
            passed=True,
            simulation_depth=0,
            explanation="No Ohio orders — no cascade risk",
        )

    start = time.monotonic()
    timeout = config.cascade_timeout_secs
    max_depth = config.max_cascade_depth

    # Build Ohio schedule sorted by existing position
    schedule = sorted(
        ohio_orders,
        key=lambda o: o.get("schedule_position", 0),
    )

    # Daily machine hours (default 8h/day)
    daily_hrs = 8.0

    # Compute original slack for each Ohio order
    today = date.today()
    order_info: list[dict] = []
    cumulative_hrs = 0.0
    for o in schedule:
        rm_hrs = o.get("rolling_mill_hours", 0.0)
        fl_hrs = o.get("finishing_line_hours", 0.0)
        order_hrs = max(rm_hrs, fl_hrs)
        cumulative_hrs += order_hrs
        due_str = o.get("due_date", "")
        try:
            due = datetime.strptime(due_str, "%Y-%m-%d").date()
            days_until = (due - today).days
        except (ValueError, TypeError):
            days_until = 0
        completion_days = cumulative_hrs / daily_hrs if daily_hrs > 0 else 0
        original_slack = days_until - completion_days
        order_info.append({
            "order_id": o.get("order_id", ""),
            "customer_id": o.get("customer_id", ""),
            "customer_tier": o.get("customer_tier", ""),
            "penalty_clause": o.get("penalty_clause", False),
            "hours": order_hrs,
            "days_until_due": days_until,
            "original_slack": round(original_slack, 1),
        })

    # Florida order hours added at end
    fl_rm = florida_order.get("rolling_mill_hours", 0.0)
    fl_fl = florida_order.get("finishing_line_hours", 0.0)
    florida_hrs = max(fl_rm, fl_fl)

    # Recalculate with Florida order inserted at end
    added_hrs = florida_hrs
    impacted: list[CascadeImpactedOrder] = []
    newly_impacted_ids: set[str] = set()

    # Level 1: direct impact from adding Florida order
    for info in order_info:
        if time.monotonic() - start > timeout:
            return CascadeImpactResult(
                passed=True,
                simulation_depth=1,
                impacted_orders=impacted,
                total_orders_impacted=len(impacted),
                has_penalty_risk=any(i.penalty_clause for i in impacted),
                timed_out=True,
                explanation=(
                    f"Cascade timed out at level 1 of {max_depth}"
                ),
            )
        new_slack = info["original_slack"] - (added_hrs / daily_hrs)
        if new_slack < 0 and info["original_slack"] >= 0:
            days_past = abs(round(new_slack))
            newly_impacted_ids.add(info["order_id"])
            impacted.append(CascadeImpactedOrder(
                order_id=info["order_id"],
                customer_id=info["customer_id"],
                customer_tier=info["customer_tier"],
                original_slack_days=round(info["original_slack"]),
                new_slack_days=round(new_slack),
                days_past_deadline=days_past,
                penalty_clause=info["penalty_clause"],
                cascade_level=1,
                impact_explanation=(
                    f"Pushed {days_past}d past deadline by "
                    f"Florida order insertion"
                ),
            ))

    # Multi-level cascade (levels 2+)
    depth_reached = 1
    prev_level_ids = newly_impacted_ids.copy()

    for depth in range(2, max_depth + 1):
        if time.monotonic() - start > timeout:
            return CascadeImpactResult(
                passed=not any(i.penalty_clause for i in impacted),
                simulation_depth=depth - 1,
                impacted_orders=impacted,
                total_orders_impacted=len(impacted),
                has_penalty_risk=any(i.penalty_clause for i in impacted),
                timed_out=True,
                explanation=(
                    f"Cascade timed out at level {depth} of {max_depth}"
                ),
            )
        if not prev_level_ids:
            break

        depth_reached = depth
        current_level_ids: set[str] = set()

        for info in order_info:
            oid = info["order_id"]
            if oid in newly_impacted_ids:
                continue
            # Check if any preceding impacted order pushes this one
            push_hrs = sum(
                i_info["hours"]
                for i_info in order_info
                if i_info["order_id"] in prev_level_ids
            )
            new_slack = info["original_slack"] - (
                (added_hrs + push_hrs) / daily_hrs
            )
            if new_slack < 0 and info["original_slack"] >= 0:
                days_past = abs(round(new_slack))
                current_level_ids.add(oid)
                newly_impacted_ids.add(oid)
                impacted.append(CascadeImpactedOrder(
                    order_id=oid,
                    customer_id=info["customer_id"],
                    customer_tier=info["customer_tier"],
                    original_slack_days=round(info["original_slack"]),
                    new_slack_days=round(new_slack),
                    days_past_deadline=days_past,
                    penalty_clause=info["penalty_clause"],
                    cascade_level=depth,
                    impact_explanation=(
                        f"Level {depth} cascade: pushed {days_past}d "
                        f"past deadline"
                    ),
                ))

        prev_level_ids = current_level_ids

    # Assess severity (BR-CM-07)
    has_penalty = any(i.penalty_clause for i in impacted)

    if not impacted:
        return CascadeImpactResult(
            passed=True,
            simulation_depth=depth_reached,
            total_orders_impacted=0,
            explanation="No Ohio orders impacted at any cascade level",
        )

    if has_penalty:
        penalty_order = next(i for i in impacted if i.penalty_clause)
        return CascadeImpactResult(
            passed=False,
            simulation_depth=depth_reached,
            impacted_orders=impacted,
            total_orders_impacted=len(impacted),
            has_penalty_risk=True,
            failure_reason=(
                f"Ohio order {penalty_order.order_id} with penalty clause "
                f"pushed {penalty_order.days_past_deadline}d past deadline"
            ),
            explanation=(
                f"{len(impacted)} Ohio orders impacted, "
                f"penalty risk on {penalty_order.order_id}"
            ),
        )

    return CascadeImpactResult(
        passed=True,
        simulation_depth=depth_reached,
        impacted_orders=impacted,
        total_orders_impacted=len(impacted),
        explanation=(
            f"Warning: {len(impacted)} Ohio orders impacted "
            f"but no penalty risk"
        ),
    )


# -------------------------------------------------------------------
# Recommendation Derivation (BR-CM-08)
# -------------------------------------------------------------------


def derive_recommendation(
    l1: EquipmentCheckResult,
    l2: MaterialCheckResult,
    l3: UtilizationCheckResult,
    l4: CascadeImpactResult,
) -> tuple[RecommendationCategory, str, list[str]]:
    """Derive composite recommendation from 4 layer results.

    Returns (category, explanation, conditions).
    """
    # Any hard failure → NON_TRANSFERABLE
    if not l1.passed or not l2.passed or not l3.passed or not l4.passed:
        reasons = []
        if not l1.passed:
            reasons.append(f"L1: {l1.failure_reason}")
        if not l2.passed:
            reasons.append(f"L2: {l2.failure_reason}")
        if not l3.passed:
            reasons.append(f"L3: {l3.failure_reason}")
        if not l4.passed:
            reasons.append(f"L4: {l4.failure_reason}")
        return (
            RecommendationCategory.NON_TRANSFERABLE,
            "; ".join(reasons),
            [],
        )

    conditions: list[str] = []
    partial_material = l2.match_status == "Partial Match"
    escalation = l3.shift_escalation_needed

    if partial_material:
        lead = l2.procurement_lead_time_days
        conditions.append(
            f"Requires procurement of {l2.shortfall_tons:.0f} tons "
            f"({lead}d lead time)"
        )
    if escalation:
        tier = l3.recommended_shift_tier
        conditions.append(f"Requires {tier.lower()} shift")

    # Multiple conditions
    if partial_material and escalation:
        return (
            RecommendationCategory.TRANSFER_WITH_CONDITIONS,
            "Multiple conditions: procurement + shift escalation",
            conditions,
        )

    if partial_material:
        return (
            RecommendationCategory.TRANSFER_WITH_PROCUREMENT,
            conditions[0],
            conditions,
        )

    if escalation:
        tier = l3.recommended_shift_tier
        if tier == "Weekend":
            return (
                RecommendationCategory.TRANSFER_ON_WEEKEND,
                conditions[0],
                conditions,
            )
        return (
            RecommendationCategory.TRANSFER_ON_OVERTIME,
            conditions[0],
            conditions,
        )

    return (
        RecommendationCategory.TRANSFER,
        "All layers passed on normal shift with full material match",
        [],
    )


# -------------------------------------------------------------------
# Top-Level Funnel Evaluation
# -------------------------------------------------------------------


def evaluate_funnel(
    order: dict,
    equipment: list[dict],
    materials: dict,
    workforce: dict,
    ohio_orders: list[dict],
    tracker: RunningCapacityTracker,
    config: AgentConfig,
) -> FunnelResult:
    """Run all 4 constraint layers and derive recommendation.

    Pure Python, deterministic. Registered as a Strands Python tool.
    """
    # Normalize common key name variations from LLM-constructed dicts
    if "orderId" in order and "order_id" not in order:
        order["order_id"] = order["orderId"]
    if "productFamily" in order and "product_family" not in order:
        order["product_family"] = order["productFamily"]
    if "dueDate" in order and "due_date" not in order:
        order["due_date"] = order["dueDate"]
    if "orderValue" in order and "order_value" not in order:
        order["order_value"] = order["orderValue"]
    if "customerId" in order and "customer_id" not in order:
        order["customer_id"] = order["customerId"]
    if "customerTier" in order and "customer_tier" not in order:
        order["customer_tier"] = order["customerTier"]
    if "rollingMillHours" in order and "rolling_mill_hours" not in order:
        order["rolling_mill_hours"] = order["rollingMillHours"]
    if "finishingLineHours" in order and "finishing_line_hours" not in order:
        order["finishing_line_hours"] = order["finishingLineHours"]
    if "rawMaterialTons" in order and "raw_material_tons" not in order:
        order["raw_material_tons"] = order["rawMaterialTons"]

    order_id = order.get("order_id", "")
    priority = order.get("priority", "P3")

    l1 = check_equipment_compatibility(order, equipment)
    l2 = check_material_availability(order, materials, tracker)
    l3 = check_utilization_and_workforce(order, tracker, workforce, config)
    l4 = simulate_cascade(order, ohio_orders, config)

    all_passed = l1.passed and l2.passed and l3.passed and l4.passed
    category, explanation, conditions = derive_recommendation(l1, l2, l3, l4)

    logger.info(
        "Funnel evaluated",
        extra={
            "order_id": order_id,
            "priority": priority,
            "l1_passed": l1.passed,
            "l2_passed": l2.passed,
            "l3_passed": l3.passed,
            "l4_passed": l4.passed,
            "recommendation": category.value,
        },
    )

    return FunnelResult(
        order_id=order_id,
        priority=priority,
        layer1_equipment=l1,
        layer2_material=l2,
        layer3_utilization=l3,
        layer4_cascade=l4,
        all_layers_passed=all_passed,
        recommendation=category.value,
        recommendation_category=category,
        recommendation_explanation=explanation,
        conditions=conditions,
    )
