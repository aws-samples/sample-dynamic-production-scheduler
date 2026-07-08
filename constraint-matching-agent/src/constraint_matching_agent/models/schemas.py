"""Pydantic schema models for the Constraint Matching Agent.

Covers: agent configuration, funnel layer results, composite funnel result,
recommendation categories, running capacity tracker, planner decisions,
skip queue, input/output contracts, and audit entries.
"""

from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Agent Configuration
# ---------------------------------------------------------------------------


class AgentConfig(BaseModel):
    """Business-configurable thresholds for constraint matching."""

    utilization_warning_pct: float = Field(0.90, ge=0.0, le=1.0)
    max_cascade_depth: int = Field(5, ge=1)
    cascade_timeout_secs: int = Field(3, ge=1)
    checkpoint_interval_secs: int = Field(300, ge=1)


# ---------------------------------------------------------------------------
# Recommendation Categories
# ---------------------------------------------------------------------------


class RecommendationCategory(str, Enum):
    """Transfer recommendation outcomes."""

    TRANSFER = "Transfer"
    TRANSFER_WITH_PROCUREMENT = "Transfer with procurement"
    TRANSFER_ON_OVERTIME = "Transfer on overtime"
    TRANSFER_ON_WEEKEND = "Transfer on weekend"
    TRANSFER_WITH_CONDITIONS = "Transfer with conditions"
    NON_TRANSFERABLE = "Non-transferable"


# ---------------------------------------------------------------------------
# Layer 1: Equipment Compatibility
# ---------------------------------------------------------------------------


class EquipmentCheckResult(BaseModel):
    """Result of Layer 1 equipment compatibility check."""

    passed: bool
    rolling_mill_compatible: bool = True
    finishing_line_compatible: bool = True
    gauge_in_range: bool = True
    gauge_order: float | None = None
    gauge_machine_min: float | None = None
    gauge_machine_max: float | None = None
    failure_reason: str | None = None
    explanation: str = ""


# ---------------------------------------------------------------------------
# Layer 2: Material Availability
# ---------------------------------------------------------------------------


class MaterialCheckResult(BaseModel):
    """Result of Layer 2 material availability check."""

    passed: bool
    match_status: str = Field(
        ..., pattern=r"^(Full Match|Partial Match|No Match)$"
    )
    required_tons: float = Field(..., ge=0.0)
    available_surplus_tons: float = Field(0.0, ge=0.0)
    shortfall_tons: float = Field(0.0, ge=0.0)
    procurement_lead_time_days: int = Field(0, ge=0)
    production_time_days: float = Field(0.0, ge=0.0)
    days_until_due_date: int = 0
    procurement_feasible: bool = False
    failure_reason: str | None = None
    explanation: str = ""


# ---------------------------------------------------------------------------
# Layer 3: Machine Utilization + Workforce
# ---------------------------------------------------------------------------


class ShiftEscalationOption(BaseModel):
    """Available shift escalation tier."""

    shift_tier: str = Field(..., pattern=r"^(Overtime|Weekend)$")
    rolling_mill_surplus_hrs: float = Field(0.0, ge=0.0)
    finishing_line_surplus_hrs: float = Field(0.0, ge=0.0)
    workforce_note: str = ""


class UtilizationCheckResult(BaseModel):
    """Result of Layer 3 utilization and workforce check."""

    passed: bool
    rolling_mill_available_hrs: float = Field(0.0, ge=0.0)
    rolling_mill_required_hrs: float = Field(0.0, ge=0.0)
    finishing_line_available_hrs: float = Field(0.0, ge=0.0)
    finishing_line_required_hrs: float = Field(0.0, ge=0.0)
    recommended_shift_tier: str = Field(
        "Normal", pattern=r"^(Normal|Overtime|Weekend)$"
    )
    shift_escalation_needed: bool = False
    escalation_options: list[ShiftEscalationOption] = []
    utilization_warning: bool = False
    workforce_sufficient: bool = True
    workforce_available: int = Field(0, ge=0)
    workforce_required: int = Field(0, ge=0)
    workforce_constraint_type: str = Field(
        "hard", pattern=r"^(hard|soft)$"
    )
    failure_reason: str | None = None
    explanation: str = ""


# ---------------------------------------------------------------------------
# Layer 4: Cascade Impact
# ---------------------------------------------------------------------------


class CascadeImpactedOrder(BaseModel):
    """Ohio order impacted by cascade simulation."""

    order_id: str = Field(..., pattern=r"^PO-\d{4}-\d{3}$")
    customer_id: str = ""
    customer_tier: str = ""
    original_slack_days: int = 0
    new_slack_days: int = 0
    days_past_deadline: int = Field(0, ge=0)
    penalty_clause: bool = False
    cascade_level: int = Field(1, ge=1)
    impact_explanation: str = ""


class CascadeImpactResult(BaseModel):
    """Result of Layer 4 cascade impact simulation."""

    passed: bool
    simulation_depth: int = Field(0, ge=0)
    impacted_orders: list[CascadeImpactedOrder] = []
    total_orders_impacted: int = Field(0, ge=0)
    has_penalty_risk: bool = False
    timed_out: bool = False
    failure_reason: str | None = None
    explanation: str = ""


# ---------------------------------------------------------------------------
# Composite Funnel Result
# ---------------------------------------------------------------------------


class FunnelResult(BaseModel):
    """Composite result of all 4 constraint funnel layers."""

    order_id: str = Field(..., pattern=r"^PO-\d{4}-\d{3}$")
    priority: str = Field(..., pattern=r"^(P1|P2|P3)$")
    layer1_equipment: EquipmentCheckResult
    layer2_material: MaterialCheckResult
    layer3_utilization: UtilizationCheckResult
    layer4_cascade: CascadeImpactResult
    all_layers_passed: bool = False
    recommendation: str = ""
    recommendation_category: RecommendationCategory = (
        RecommendationCategory.NON_TRANSFERABLE
    )
    recommendation_explanation: str = ""
    conditions: list[str] = []


# ---------------------------------------------------------------------------
# Running Capacity Tracker
# ---------------------------------------------------------------------------


class RunningShiftHours(BaseModel):
    """Remaining hours per shift tier for a machine type."""

    normal_hrs: float = Field(0.0, ge=0.0)
    overtime_hrs: float = Field(0.0, ge=0.0)
    weekend_hrs: float = Field(0.0, ge=0.0)
    total_hrs: float = Field(0.0, ge=0.0)


class ProcessedOrderEntry(BaseModel):
    """Record of a processed order decision."""

    order_id: str = Field(..., pattern=r"^PO-\d{4}-\d{3}$")
    decision: str = Field(..., pattern=r"^(approved|rejected|skipped)$")
    recommendation_category: str = ""
    rolling_mill_hrs_consumed: float = Field(0.0, ge=0.0)
    finishing_line_hrs_consumed: float = Field(0.0, ge=0.0)
    material_tons_consumed: float = Field(0.0, ge=0.0)
    decided_at: str = ""


class RunningCapacityTracker(BaseModel):
    """Persisted running capacity state across order decisions."""

    session_id: str
    last_updated: str = ""
    rolling_mill_remaining_hrs: RunningShiftHours = Field(
        default_factory=RunningShiftHours
    )
    finishing_line_remaining_hrs: RunningShiftHours = Field(
        default_factory=RunningShiftHours
    )
    material_remaining_tons: float = Field(0.0, ge=0.0)
    workforce_remaining: int = Field(0, ge=0)
    orders_processed: list[ProcessedOrderEntry] = []
    orders_skipped: list[str] = []
    orders_approved: list[str] = []
    orders_rejected: list[str] = []


# ---------------------------------------------------------------------------
# Planner Decision Entities
# ---------------------------------------------------------------------------


class CapacityConsumed(BaseModel):
    """Capacity consumed by an approved order."""

    rolling_mill_hrs: float = Field(0.0, ge=0.0)
    finishing_line_hrs: float = Field(0.0, ge=0.0)
    material_tons: float = Field(0.0, ge=0.0)
    operator_hrs: float = Field(0.0, ge=0.0)
    shift_tier_used: str = Field(
        "Normal", pattern=r"^(Normal|Overtime|Weekend)$"
    )


class OrderDecision(BaseModel):
    """Planner decision on a single order."""

    order_id: str = Field(..., pattern=r"^PO-\d{4}-\d{3}$")
    action: str = Field(..., pattern=r"^(approve|reject|skip)$")
    decided_at: str = ""


class OrderDecisionResult(BaseModel):
    """Result after processing a planner decision."""

    order_id: str = Field(..., pattern=r"^PO-\d{4}-\d{3}$")
    action: str
    recommendation_category: str = ""
    capacity_consumed: CapacityConsumed | None = None
    tracker_updated: bool = False
    next_order_id: str | None = None
    explanation: str = ""


# ---------------------------------------------------------------------------
# Skip Queue
# ---------------------------------------------------------------------------


class SkipQueueEntry(BaseModel):
    """Entry in the skip queue for deferred orders."""

    order_id: str = Field(..., pattern=r"^PO-\d{4}-\d{3}$")
    priority: str = Field(..., pattern=r"^(P1|P2|P3)$")
    skipped_at: str = ""
    original_position: int = Field(0, ge=0)
    revisit_requested: bool = False


# ---------------------------------------------------------------------------
# Input Validation
# ---------------------------------------------------------------------------


class OrderDecisionInput(BaseModel):
    """Validated input for planner decision."""

    order_id: str = Field(..., pattern=r"^PO-\d{4}-\d{3}$")
    action: str = Field(..., pattern=r"^(approve|reject|skip)$")
    reason: str = Field(default="", max_length=500)


class RevisitInput(BaseModel):
    """Validated input for order revisit request."""

    order_id: str = Field(..., pattern=r"^PO-\d{4}-\d{3}$")


# ---------------------------------------------------------------------------
# Transfer Summary
# ---------------------------------------------------------------------------


class TransferSummary(BaseModel):
    """Summary after all orders processed."""

    total_orders_evaluated: int = Field(0, ge=0)
    orders_approved: int = Field(0, ge=0)
    orders_rejected: int = Field(0, ge=0)
    orders_skipped: int = Field(0, ge=0)
    total_rm_hrs_consumed: float = Field(0.0, ge=0.0)
    total_fl_hrs_consumed: float = Field(0.0, ge=0.0)
    total_material_consumed: float = Field(0.0, ge=0.0)
    summary_text: str = ""


# ---------------------------------------------------------------------------
# Audit Entry
# ---------------------------------------------------------------------------


class ConstraintMatchingAuditEntry(BaseModel):
    """Audit entry for constraint matching decisions."""

    session_id: str
    agent: str = "constraint_matching_agent"
    action: str = Field(
        ...,
        pattern=(
            r"^(funnel_evaluation|order_decision|order_skip"
            r"|order_revisit|tracker_update)$"
        ),
    )
    timestamp: str
    details: dict


# ---------------------------------------------------------------------------
# Structured Output (Strands structured_output_model)
# ---------------------------------------------------------------------------


class FunnelLayerSummary(BaseModel):
    """Single funnel layer result for structured output."""

    layer: int
    name: str
    passed: bool
    detail: str = ""


class FunnelOrderSummary(BaseModel):
    """Per-order funnel result for structured output."""

    order_id: str
    priority: str
    product_family: str = ""
    customer_id: str = ""
    customer_tier: str = ""
    order_value: float = 0.0
    due_date: str = ""
    all_layers_passed: bool = False
    recommendation: str = ""
    recommendation_category: str = "Non-transferable"
    reasoning: str = ""
    layers: list[FunnelLayerSummary] = []


class ConstraintMatchingOutput(BaseModel):
    """Structured output for Constraint Matching Agent.

    Used as structured_output_model in Agent() constructor.
    Contains funnel results per order with per-layer pass/fail,
    recommendation, and reasoning.
    """

    funnel_results: list[FunnelOrderSummary] = []
    transfer_summary: TransferSummary | None = None
    summary_text: str = ""
