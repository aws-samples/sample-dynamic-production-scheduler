"""Pure Python capacity engine.

Deterministic — same input always produces same output.
No LLM calls. Registered as Strands Python tools so the
LLM can invoke calculations after fetching data via MCP tools.

Implements: BR-CO-01 through BR-CO-18.
"""

from __future__ import annotations

import logging
from copy import deepcopy
from datetime import date, datetime
from typing import Any

from capacity_optimization_agent.models.schemas import (
    BottleneckInfo,
    CapacitySnapshot,
    DelayCandidateInfo,
    DelayDecision,
    DelayResult,
    ConstraintImpact,
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

logger = logging.getLogger("capacity_optimization_agent")


# -------------------------------------------------------------------
# Shift utilization (BR-CO-03)
# -------------------------------------------------------------------

def compute_shift_utilization(
    total_hours: float,
    committed_hours: float,
    shift_type: str,
) -> ShiftUtilization:
    """Build a single shift tier's utilization."""
    surplus = max(total_hours - committed_hours, 0.0)
    pct = min((committed_hours / total_hours * 100.0), 100.0) if total_hours > 0 else 0.0
    return ShiftUtilization(
        shift_type=shift_type,
        total_hours=round(total_hours, 2),
        committed_hours=round(committed_hours, 2),
        surplus_hours=round(surplus, 2),
        utilization_pct=round(pct, 2),
    )


def compute_machine_utilization(
    machine_type: str,
    normal_total: float,
    normal_committed: float,
    overtime_total: float,
    weekend_total: float,
) -> MachineUtilization:
    """Tiered utilization for one machine type (BR-CO-03)."""
    normal = compute_shift_utilization(normal_total, normal_committed, "Normal")
    overtime = compute_shift_utilization(overtime_total, 0.0, "Overtime")
    weekend = compute_shift_utilization(weekend_total, 0.0, "Weekend")

    total_surplus = normal.surplus_hours + overtime.surplus_hours + weekend.surplus_hours
    # Effective surplus: normal first, then OT, then weekend
    effective = normal.surplus_hours

    return MachineUtilization(
        machine_type=machine_type,
        normal=normal,
        overtime=overtime,
        weekend=weekend,
        total_surplus_hours=round(total_surplus, 2),
        effective_surplus_hours=round(effective, 2),
    )


# -------------------------------------------------------------------
# Bottleneck identification (BR-CO-04)
# -------------------------------------------------------------------

def identify_bottleneck(
    utilization_list: list[MachineUtilization],
    florida_demand: dict[str, float],
) -> BottleneckInfo:
    """Ratio-based bottleneck: lowest surplus-to-demand ratio (BR-CO-04)."""
    if not utilization_list:
        return BottleneckInfo(
            machine_type="Unknown",
            surplus_to_demand_ratio=0.0,
            explanation="No machine utilization data available",
        )

    ratios: dict[str, float] = {}
    surplus_map: dict[str, float] = {}
    demand_map: dict[str, float] = {}

    for mu in utilization_list:
        surplus = mu.total_surplus_hours
        demand = florida_demand.get(mu.machine_type, 0.0)
        surplus_map[mu.machine_type] = surplus
        demand_map[mu.machine_type] = demand
        ratios[mu.machine_type] = surplus / demand if demand > 0 else float("inf")

    # Lowest ratio = bottleneck; tiebreaker: Rolling Mill (BR-CO-04)
    bottleneck = min(
        ratios,
        key=lambda m: (ratios[m], 0 if m == "Rolling Mill" else 1),
    )

    ratio = ratios[bottleneck]
    surplus = surplus_map[bottleneck]
    demand = demand_map[bottleneck]

    other_machines = [m for m in ratios if m != bottleneck]
    other_info = ", ".join(
        f"{m} at {ratios[m]:.0%} coverage" for m in other_machines
    )
    explanation = (
        f"{bottleneck} is the constraint at {ratio:.0%} capacity coverage "
        f"({surplus:.0f} surplus hours vs {demand:.0f} hours of Florida demand)."
    )
    if other_info:
        explanation += f" {other_info}."

    return BottleneckInfo(
        machine_type=bottleneck,
        surplus_to_demand_ratio=round(ratio, 4),
        surplus_hours=round(surplus, 2),
        demand_hours=round(demand, 2),
        explanation=explanation,
    )


# -------------------------------------------------------------------
# Surplus summary (BR-CO-03)
# -------------------------------------------------------------------

def build_surplus_summary(
    utilization_list: list[MachineUtilization],
    materials: list[MaterialSurplus],
    workforce: WorkforceAvailability | None,
) -> SurplusSummary:
    """Aggregate surplus across all dimensions."""
    rm_n = rm_o = rm_w = 0.0
    fl_n = fl_o = fl_w = 0.0

    for mu in utilization_list:
        if mu.machine_type == "Rolling Mill":
            rm_n = mu.normal.surplus_hours
            rm_o = mu.overtime.surplus_hours
            rm_w = mu.weekend.surplus_hours
        elif mu.machine_type == "Finishing Line":
            fl_n = mu.normal.surplus_hours
            fl_o = mu.overtime.surplus_hours
            fl_w = mu.weekend.surplus_hours

    mat_surplus = sum(m.available_surplus_tons for m in materials)
    mp_surplus = workforce.available_surplus if workforce else 0

    return SurplusSummary(
        rolling_mill_normal_hrs=round(rm_n, 2),
        rolling_mill_overtime_hrs=round(rm_o, 2),
        rolling_mill_weekend_hrs=round(rm_w, 2),
        finishing_line_normal_hrs=round(fl_n, 2),
        finishing_line_overtime_hrs=round(fl_o, 2),
        finishing_line_weekend_hrs=round(fl_w, 2),
        total_material_surplus_tons=round(mat_surplus, 2),
        total_workforce_surplus=mp_surplus,
    )


# -------------------------------------------------------------------
# Slack calculation (BR-CO-17)
# -------------------------------------------------------------------

def compute_slack_days(
    due_date_str: str,
    rolling_mill_hours: float,
    finishing_line_hours: float,
    daily_machine_hours: float,
) -> int:
    """Slack = due_date - today - estimated_production_days (BR-CO-17)."""
    today = date.today()
    try:
        due = datetime.strptime(due_date_str, "%Y-%m-%d").date()
    except (ValueError, TypeError):
        logger.warning("Invalid due_date '%s', defaulting slack=0", due_date_str)
        return 0

    if daily_machine_hours <= 0:
        return (due - today).days

    production_days = max(rolling_mill_hours, finishing_line_hours) / daily_machine_hours
    return int((due - today).days - production_days)


# -------------------------------------------------------------------
# Order enrichment (BR-CO-06, BR-CO-17)
# -------------------------------------------------------------------

def enrich_orders(
    raw_orders: list[dict[str, Any]],
    customers: dict[str, dict[str, Any]],
    equipment: list[EquipmentCapability],
) -> list[OhioOrderLoad]:
    """Parse raw MCP order data into OhioOrderLoad with slack (BR-CO-17)."""
    # Compute daily machine hours from first equipment entry
    daily_hrs = 8.0  # fallback
    for eq in equipment:
        if eq.net_available_hours_per_week > 0:
            daily_hrs = eq.net_available_hours_per_week / 5.0
            break

    result: list[OhioOrderLoad] = []
    for o in raw_orders:
        cust_id = o.get("customer_id", "")
        cust = customers.get(cust_id, {})
        penalty = cust.get("penalty_clause", o.get("penalty_clause", False))

        rm_hrs = o.get("rolling_mill_hours", 0.0)
        fl_hrs = o.get("finishing_line_hours", 0.0)

        slack = compute_slack_days(
            o.get("due_date", ""),
            rm_hrs,
            fl_hrs,
            daily_hrs,
        )

        result.append(OhioOrderLoad(
            order_id=o["order_id"],
            product_family=o.get("product_family", ""),
            customer_id=cust_id,
            customer_tier=o.get("customer_tier", cust.get("customer_tier", "Tier3")),
            due_date=o.get("due_date", ""),
            quantity=o.get("quantity", 0),
            order_value=o.get("order_value", 0.0),
            priority=o.get("priority"),
            rolling_mill_hours=rm_hrs,
            finishing_line_hours=fl_hrs,
            raw_material_tons=o.get("raw_material_tons", 0.0),
            slack_days=slack,
            penalty_clause=penalty,
        ))

    return result


# -------------------------------------------------------------------
# Delay candidate filtering (BR-CO-06, BR-CO-07, BR-CO-08, BR-CO-09)
# -------------------------------------------------------------------

def filter_delay_candidates(
    orders: list[OhioOrderLoad],
    delay_threshold_days: int,
    workforce: WorkforceAvailability | None,
    bottleneck_machine: str,
) -> list[DelayCandidateInfo]:
    """Identify P3 orders eligible for delay (BR-CO-06)."""
    ops_per_rm = workforce.operators_per_rolling_mill if workforce else 1
    ops_per_fl = workforce.operators_per_finishing_line if workforce else 1

    candidates: list[DelayCandidateInfo] = []
    for o in orders:
        # BR-CO-06: P3 or unclassified, slack > threshold, no penalty
        if o.priority not in ("P3", None):
            continue
        if o.slack_days <= delay_threshold_days:
            continue
        if o.penalty_clause:
            continue

        freed_op_hrs = (
            o.rolling_mill_hours * ops_per_rm
            + o.finishing_line_hours * ops_per_fl
        )
        remaining_buffer = o.slack_days - delay_threshold_days

        # BR-CO-09: risk assessment
        if remaining_buffer > 21:
            risk = "Low"
        elif remaining_buffer > 7:
            risk = "Medium"
        else:
            risk = "High"

        explanation = (
            f"Order {o.order_id} frees {o.rolling_mill_hours:.0f} Rolling Mill hours "
            f"and {o.finishing_line_hours:.0f} Finishing Line hours. "
            f"{remaining_buffer}-day buffer remains after delay. {risk} risk."
        )
        if not o.penalty_clause:
            explanation += " Customer has no penalty clause."

        candidates.append(DelayCandidateInfo(
            order_id=o.order_id,
            product_family=o.product_family,
            customer_id=o.customer_id,
            customer_tier=o.customer_tier,
            due_date=o.due_date,
            quantity=o.quantity,
            order_value=o.order_value,
            priority="P3",
            slack_days=o.slack_days,
            penalty_clause=o.penalty_clause,
            freed_rolling_mill_hours=o.rolling_mill_hours,
            freed_finishing_line_hours=o.finishing_line_hours,
            freed_material_tons=o.raw_material_tons,
            freed_operator_hours=round(freed_op_hrs, 2),
            remaining_buffer_days=remaining_buffer,
            risk_level=risk,
            trade_off_explanation=explanation,
        ))

    # BR-CO-07: sort by freed bottleneck hours desc, total freed desc, due_date asc
    def sort_key(c: DelayCandidateInfo) -> tuple:
        bottleneck_freed = (
            c.freed_rolling_mill_hours
            if bottleneck_machine == "Rolling Mill"
            else c.freed_finishing_line_hours
        )
        total_freed = c.freed_rolling_mill_hours + c.freed_finishing_line_hours
        return (-bottleneck_freed, -total_freed, c.due_date)

    candidates.sort(key=sort_key)
    return candidates


# -------------------------------------------------------------------
# Cached Snapshot State (Pattern 8)
# -------------------------------------------------------------------

class CapacityState:
    """In-memory cache for fast recalculations (Pattern 8).

    After initial capacity analysis, delay decisions and constraint
    applications operate on cached data — no MCP re-fetch needed.
    """

    def __init__(self, snapshot: CapacitySnapshot):
        self._snapshot = deepcopy(snapshot)

    @property
    def snapshot(self) -> CapacitySnapshot:
        return self._snapshot

    def apply_delay(
        self,
        order_id: str,
        freed_rm: float,
        freed_fl: float,
        freed_material: float,
        freed_operators: int,
        florida_demand: dict[str, float],
    ) -> CapacitySnapshot:
        """Add freed capacity from approved delay, recalculate (BR-CO-10)."""
        s = self._snapshot

        # Update utilization surplus
        for mu in s.utilization:
            if mu.machine_type == "Rolling Mill":
                mu.normal = compute_shift_utilization(
                    mu.normal.total_hours,
                    max(mu.normal.committed_hours - freed_rm, 0.0),
                    "Normal",
                )
                mu.total_surplus_hours = (
                    mu.normal.surplus_hours
                    + mu.overtime.surplus_hours
                    + mu.weekend.surplus_hours
                )
                mu.effective_surplus_hours = mu.normal.surplus_hours
            elif mu.machine_type == "Finishing Line":
                mu.normal = compute_shift_utilization(
                    mu.normal.total_hours,
                    max(mu.normal.committed_hours - freed_fl, 0.0),
                    "Normal",
                )
                mu.total_surplus_hours = (
                    mu.normal.surplus_hours
                    + mu.overtime.surplus_hours
                    + mu.weekend.surplus_hours
                )
                mu.effective_surplus_hours = mu.normal.surplus_hours

        # Update workforce
        if s.workforce:
            s.workforce.available_surplus = min(
                s.workforce.available_surplus + freed_operators,
                s.workforce.total_operators,
            )

        # Update materials
        remaining_freed = freed_material
        for mat in s.materials:
            if remaining_freed <= 0:
                break
            mat.available_surplus_tons += remaining_freed
            remaining_freed = 0.0

        # Recalculate surplus summary and bottleneck
        s.total_surplus_summary = build_surplus_summary(
            s.utilization, s.materials, s.workforce,
        )
        s.bottleneck = identify_bottleneck(s.utilization, florida_demand)

        return s

    def apply_constraint(
        self,
        constraint: PlannerConstraint,
        florida_demand: dict[str, float],
    ) -> ConstraintImpact:
        """Apply constraint globally, recalculate (BR-CO-11, BR-CO-12)."""
        s = self._snapshot
        before_summary = deepcopy(s.total_surplus_summary)
        before_bottleneck = deepcopy(s.bottleneck)

        text_lower = constraint.constraint_text.lower()

        if constraint.constraint_type == "shift_restriction":
            for mu in s.utilization:
                if "weekend" in text_lower:
                    mu.weekend = compute_shift_utilization(0.0, 0.0, "Weekend")
                if "overtime" in text_lower or "no overtime" in text_lower:
                    mu.overtime = compute_shift_utilization(0.0, 0.0, "Overtime")
                mu.total_surplus_hours = (
                    mu.normal.surplus_hours
                    + mu.overtime.surplus_hours
                    + mu.weekend.surplus_hours
                )
                mu.effective_surplus_hours = mu.normal.surplus_hours

        elif constraint.constraint_type == "capacity_limit":
            # Extract percentage from text like "Cap at 80%"
            import re
            match = re.search(r"(\d+)%", constraint.constraint_text)
            if match:
                cap_pct = int(match.group(1)) / 100.0
                for mu in s.utilization:
                    if mu.machine_type.lower() in text_lower or "all" in text_lower:
                        mu.normal = compute_shift_utilization(
                            mu.normal.total_hours * cap_pct,
                            mu.normal.committed_hours,
                            "Normal",
                        )
                        mu.total_surplus_hours = (
                            mu.normal.surplus_hours
                            + mu.overtime.surplus_hours
                            + mu.weekend.surplus_hours
                        )
                        mu.effective_surplus_hours = mu.normal.surplus_hours

        # Add to active constraints
        s.active_constraints.append(constraint.constraint_text)

        # Recalculate
        s.total_surplus_summary = build_surplus_summary(
            s.utilization, s.materials, s.workforce,
        )
        s.bottleneck = identify_bottleneck(s.utilization, florida_demand)

        return ConstraintImpact(
            constraint=constraint,
            capacity_before=before_summary,
            capacity_after=s.total_surplus_summary,
            bottleneck_before=before_bottleneck,
            bottleneck_after=s.bottleneck,
        )


# -------------------------------------------------------------------
# Delay result builder (BR-CO-10, BR-CO-18)
# -------------------------------------------------------------------

def build_delay_result(
    decisions: list[DelayDecision],
    before_summary: SurplusSummary,
    before_bottleneck: BottleneckInfo,
    after_summary: SurplusSummary,
    after_bottleneck: BottleneckInfo,
) -> DelayResult:
    """Build before/after comparison for delay decisions."""
    return DelayResult(
        decisions=decisions,
        capacity_before=before_summary,
        capacity_after=after_summary,
        bottleneck_before=before_bottleneck,
        bottleneck_after=after_bottleneck,
    )


# -------------------------------------------------------------------
# Shared context builder (BR-CO-18)
# -------------------------------------------------------------------

def build_shared_snapshot(
    snapshot: CapacitySnapshot,
    delays_approved: list[str],
) -> SharedCapacitySnapshot:
    """Build the payload for AgentCore Memory."""
    return SharedCapacitySnapshot(
        session_id=snapshot.session_id,
        analyzed_at=snapshot.analyzed_at,
        rerouting_window_days=snapshot.rerouting_window_days,
        bottleneck=snapshot.bottleneck,
        surplus_summary=snapshot.total_surplus_summary,
        active_constraints=snapshot.active_constraints,
        delays_approved=delays_approved,
    )


# -------------------------------------------------------------------
# Utilization warning (BR-CO-05)
# -------------------------------------------------------------------

def check_utilization_warnings(
    utilization_list: list[MachineUtilization],
    warning_pct: float,
) -> list[str]:
    """Flag machines with normal shift utilization above threshold."""
    warnings: list[str] = []
    threshold = warning_pct * 100.0  # convert to percentage
    for mu in utilization_list:
        if mu.normal.utilization_pct >= threshold:
            warnings.append(
                f"{mu.machine_type} normal shift at "
                f"{mu.normal.utilization_pct:.0f}% utilization "
                f"— overtime escalation likely"
            )
    return warnings
