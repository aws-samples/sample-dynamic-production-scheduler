"""Pydantic schema models for the Capacity & Optimization Agent.

Covers: capacity configuration, shift utilization, machine utilization,
workforce, materials, order load, bottleneck, surplus summary,
delay candidates, constraints, and shared context.
"""

from __future__ import annotations

from pydantic import BaseModel, Field, field_validator


# ---------------------------------------------------------------------------
# Agent Configuration Schemas
# ---------------------------------------------------------------------------


class CapacityAgentConfig(BaseModel):
    """Business-configurable thresholds for capacity analysis."""

    rerouting_window_days: int = Field(10, ge=1)
    delay_threshold_days: int = Field(42, ge=1)
    utilization_warning_pct: float = Field(0.90, ge=0.0, le=1.0)


# ---------------------------------------------------------------------------
# Capacity Dimension Entities
# ---------------------------------------------------------------------------


class EquipmentCapability(BaseModel):
    """Machine capability data from ERP Data MCP."""

    machine_type: str
    product_families_supported: list[str] = []
    total_hours_per_week: float = Field(..., ge=0.0)
    planned_downtime_hrs_week: float = Field(0.0, ge=0.0)
    net_available_hours_per_week: float = Field(..., ge=0.0)
    gauge_range_min: float | None = None
    gauge_range_max: float | None = None
    setup_time_by_family: dict[str, float] = {}


class ShiftUtilization(BaseModel):
    """Hours breakdown for a single shift tier."""

    shift_type: str = Field(..., pattern=r"^(Normal|Overtime|Weekend)$")
    total_hours: float = Field(..., ge=0.0)
    committed_hours: float = Field(0.0, ge=0.0)
    surplus_hours: float = Field(0.0, ge=0.0)
    utilization_pct: float = Field(0.0, ge=0.0, le=100.0)


class MachineUtilization(BaseModel):
    """Tiered utilization for a single machine type."""

    machine_type: str
    normal: ShiftUtilization
    overtime: ShiftUtilization
    weekend: ShiftUtilization
    total_surplus_hours: float = Field(0.0, ge=0.0)
    effective_surplus_hours: float = Field(0.0, ge=0.0)

    @property
    def normal_utilization_pct(self) -> float:
        """Convenience accessor matching the structured output field name."""
        return self.normal.utilization_pct


class WorkforceAvailability(BaseModel):
    """Workforce dimension from ERP Data MCP."""

    total_operators: int = Field(..., ge=0)
    currently_allocated: int = Field(0, ge=0)
    available_surplus: int = Field(0, ge=0)
    overtime_hrs_per_shift: float = Field(0.0, ge=0.0)
    weekend_hrs_per_shift: float = Field(0.0, ge=0.0)
    operators_per_rolling_mill: int = Field(1, ge=0)
    operators_per_finishing_line: int = Field(1, ge=0)


class MaterialSurplus(BaseModel):
    """Raw material surplus for a single material type."""

    material_type: str
    current_inventory_tons: float = Field(..., ge=0.0)
    committed_to_orders_tons: float = Field(0.0, ge=0.0)
    available_surplus_tons: float = Field(0.0, ge=0.0)
    procurement_lead_time_days: int = Field(0, ge=0)
    unit_cost: float = Field(0.0, ge=0.0)


class OhioOrderLoad(BaseModel):
    """Existing Ohio order consuming capacity."""

    order_id: str = Field(..., pattern=r"^PO-\d{4}-\d{3}$")
    product_family: str
    customer_id: str
    customer_tier: str = Field(..., pattern=r"^(Tier1|Tier2|Tier3)$")
    due_date: str  # YYYY-MM-DD
    quantity: int = Field(..., ge=0)
    order_value: float = Field(..., ge=0.0)
    priority: str | None = None
    rolling_mill_hours: float = Field(0.0, ge=0.0)
    finishing_line_hours: float = Field(0.0, ge=0.0)
    raw_material_tons: float = Field(0.0, ge=0.0)
    slack_days: int = 0
    penalty_clause: bool = False


# ---------------------------------------------------------------------------
# Capacity Snapshot (Composite)
# ---------------------------------------------------------------------------


class SurplusSummary(BaseModel):
    """Aggregated surplus across all dimensions."""

    rolling_mill_normal_hrs: float = Field(0.0, ge=0.0)
    rolling_mill_overtime_hrs: float = Field(0.0, ge=0.0)
    rolling_mill_weekend_hrs: float = Field(0.0, ge=0.0)
    finishing_line_normal_hrs: float = Field(0.0, ge=0.0)
    finishing_line_overtime_hrs: float = Field(0.0, ge=0.0)
    finishing_line_weekend_hrs: float = Field(0.0, ge=0.0)
    total_material_surplus_tons: float = Field(0.0, ge=0.0)
    total_workforce_surplus: int = Field(0, ge=0)


class BottleneckInfo(BaseModel):
    """Bottleneck identification result (BR-CO-04)."""

    machine_type: str
    surplus_to_demand_ratio: float = Field(..., ge=0.0)
    surplus_hours: float = Field(0.0, ge=0.0)
    demand_hours: float = Field(0.0, ge=0.0)
    explanation: str = ""


class CapacitySnapshot(BaseModel):
    """Full capacity analysis result — composite of all dimensions."""

    session_id: str
    analyzed_at: str
    rerouting_window_days: int = Field(10, ge=1)
    equipment: list[EquipmentCapability] = []
    utilization: list[MachineUtilization] = []
    workforce: WorkforceAvailability | None = None
    materials: list[MaterialSurplus] = []
    existing_load: list[OhioOrderLoad] = []
    bottleneck: BottleneckInfo | None = None
    active_constraints: list[str] = []
    total_surplus_summary: SurplusSummary | None = None


# ---------------------------------------------------------------------------
# Delay Candidate Entities
# ---------------------------------------------------------------------------


class DelayCandidateInfo(BaseModel):
    """P3 order eligible for delay with freed capacity details."""

    order_id: str = Field(..., pattern=r"^PO-\d{4}-\d{3}$")
    product_family: str
    customer_id: str
    customer_tier: str = Field(..., pattern=r"^(Tier1|Tier2|Tier3)$")
    due_date: str
    quantity: int = Field(..., ge=0)
    order_value: float = Field(..., ge=0.0)
    priority: str = "P3"
    slack_days: int = 0
    penalty_clause: bool = False
    freed_rolling_mill_hours: float = Field(0.0, ge=0.0)
    freed_finishing_line_hours: float = Field(0.0, ge=0.0)
    freed_material_tons: float = Field(0.0, ge=0.0)
    freed_operator_hours: float = Field(0.0, ge=0.0)
    remaining_buffer_days: int = 0
    risk_level: str = Field("Low", pattern=r"^(Low|Medium|High)$")
    trade_off_explanation: str = ""


class DelayDecision(BaseModel):
    """Planner approval or rejection of a delay candidate."""

    order_id: str = Field(..., pattern=r"^PO-\d{4}-\d{3}$")
    approved: bool
    decided_at: str = ""


class DelayResult(BaseModel):
    """Before/after comparison for delay decisions."""

    decisions: list[DelayDecision] = []
    capacity_before: SurplusSummary | None = None
    capacity_after: SurplusSummary | None = None
    bottleneck_before: BottleneckInfo | None = None
    bottleneck_after: BottleneckInfo | None = None


# ---------------------------------------------------------------------------
# Constraint Entities
# ---------------------------------------------------------------------------


class PlannerConstraint(BaseModel):
    """Planner-added constraint with impact tracking."""

    constraint_text: str = Field(..., min_length=1, max_length=500)
    constraint_type: str = Field(
        ..., pattern=r"^(shift_restriction|capacity_limit|other)$"
    )
    applied_at: str = ""
    impact_description: str = ""


class ConstraintImpact(BaseModel):
    """Before/after comparison for a constraint application."""

    constraint: PlannerConstraint
    capacity_before: SurplusSummary | None = None
    capacity_after: SurplusSummary | None = None
    bottleneck_before: BottleneckInfo | None = None
    bottleneck_after: BottleneckInfo | None = None


# ---------------------------------------------------------------------------
# Input Validation Schemas
# ---------------------------------------------------------------------------


class DelayDecisionInput(BaseModel):
    """Validated input for delay decision tool."""

    order_id: str = Field(..., pattern=r"^PO-\d{4}-\d{3}$")
    action: str = Field(..., pattern=r"^(approve|reject)$")


class ConstraintInput(BaseModel):
    """Validated input for add-constraint tool."""

    constraint_text: str = Field(..., min_length=1, max_length=500)
    constraint_type: str = Field(
        ..., pattern=r"^(shift_restriction|capacity_limit|other)$"
    )


# ---------------------------------------------------------------------------
# Audit
# ---------------------------------------------------------------------------


class CapacityAuditEntry(BaseModel):
    """Audit entry for capacity analysis decisions."""

    session_id: str
    agent: str = "capacity_optimization_agent"
    action: str = Field(
        ...,
        pattern=(
            r"^(capacity_analysis|delay_candidate_identification"
            r"|delay_decision|constraint_application"
            r"|capacity_recalculation)$"
        ),
    )
    timestamp: str
    details: dict


# ---------------------------------------------------------------------------
# Shared Context (AgentCore Memory)
# ---------------------------------------------------------------------------


class SharedCapacitySnapshot(BaseModel):
    """Payload written to AgentCore Memory for downstream agents."""

    session_id: str
    analyzed_at: str
    rerouting_window_days: int = Field(10, ge=1)
    bottleneck: BottleneckInfo | None = None
    surplus_summary: SurplusSummary | None = None
    active_constraints: list[str] = []
    delays_approved: list[str] = []


# ---------------------------------------------------------------------------
# Structured Output (Strands structured_output_model)
# ---------------------------------------------------------------------------


class MachineUtilizationSummary(BaseModel):
    """Simplified utilization for structured output."""

    machine_type: str
    normal_utilization_pct: float = 0.0
    total_surplus_hours: float = 0.0


class DelayCandidateSummary(BaseModel):
    """Simplified delay candidate for structured output."""

    order_id: str
    product_family: str
    customer_id: str
    customer_tier: str
    order_value: float = 0.0
    due_date: str = ""
    slack_days: int = 0
    freed_rolling_mill_hours: float = 0.0
    freed_finishing_line_hours: float = 0.0
    freed_material_tons: float = 0.0
    risk_level: str = "Low"
    trade_off_explanation: str = ""


class CapacityOptimizationOutput(BaseModel):
    """Structured output for Capacity Optimization Agent.

    Used as structured_output_model in Agent() constructor.
    Contains capacity snapshot summary, delay candidates,
    surplus, and bottleneck data for the orchestrator.
    """

    utilization: list[MachineUtilizationSummary] = []
    workforce_utilization_pct: float = 0.0
    material_utilization_pct: float = 0.0
    bottleneck: str = ""
    delay_candidates: list[DelayCandidateSummary] = []
    surplus_summary: SurplusSummary | None = None
    summary_text: str = ""
