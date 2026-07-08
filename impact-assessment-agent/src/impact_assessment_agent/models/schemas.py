"""Pydantic schema models for the Impact Assessment Agent.

Covers: scoring configuration, criterion scores, scored orders,
priority summaries, reclassification, audit entries, and shared context.
"""

from __future__ import annotations

from pydantic import BaseModel, Field, field_validator, model_validator


# ---------------------------------------------------------------------------
# Agent Configuration Schemas
# ---------------------------------------------------------------------------

class ScoringWeights(BaseModel):
    """Configurable weights for the 4 scoring criteria. Must sum to 1.0."""

    urgency: float = Field(0.40, ge=0.0, le=1.0)
    customer_tier: float = Field(0.25, ge=0.0, le=1.0)
    order_value: float = Field(0.20, ge=0.0, le=1.0)
    machine_complexity: float = Field(0.15, ge=0.0, le=1.0)

    @model_validator(mode="after")
    def weights_must_sum_to_one(self) -> "ScoringWeights":
        total = (
            self.urgency
            + self.customer_tier
            + self.order_value
            + self.machine_complexity
        )
        if abs(total - 1.0) > 0.001:
            raise ValueError(
                f"Weights must sum to 1.0 (got {total:.4f})"
            )
        return self


class PriorityThresholds(BaseModel):
    """Configurable thresholds for P1/P2/P3 classification."""

    p1: int = Field(75, ge=1, le=99)
    p2: int = Field(50, ge=1, le=99)

    @model_validator(mode="after")
    def p1_must_exceed_p2(self) -> "PriorityThresholds":
        if self.p1 <= self.p2:
            raise ValueError(
                f"P1 threshold ({self.p1}) must be > P2 threshold ({self.p2})"
            )
        return self


# ---------------------------------------------------------------------------
# Scoring Model Entities
# ---------------------------------------------------------------------------

class CriterionScores(BaseModel):
    """Individual criterion scores (0-100 each)."""

    urgency: int = Field(..., ge=0, le=100)
    customer_tier: int = Field(..., ge=0, le=100)
    order_value: int = Field(..., ge=0, le=100)
    machine_complexity: int = Field(..., ge=0, le=100)


class ScoredOrder(BaseModel):
    """An order enriched with scores and priority classification."""

    order_id: str = Field(..., pattern=r"^PO-\d{4}-\d{3}$")
    product_family: str
    customer_id: str
    customer_name: str
    customer_tier: str = Field(..., pattern=r"^(Tier1|Tier2|Tier3)$")
    due_date: str  # YYYY-MM-DD
    quantity: int = Field(..., ge=0)
    order_value: float = Field(..., ge=0.0)
    machine_types_required: list[str]
    scores: CriterionScores
    weighted_score: float = Field(..., ge=0.0, le=100.0)
    priority: str = Field(..., pattern=r"^(P1|P2|P3)$")
    manually_classified: bool = False
    original_priority: str | None = None
    rolling_mill_hours: float = Field(0.0, ge=0.0)
    finishing_line_hours: float = Field(0.0, ge=0.0)
    raw_material_tons: float = Field(0.0, ge=0.0)


# ---------------------------------------------------------------------------
# Output Contracts
# ---------------------------------------------------------------------------

class PrioritySummary(BaseModel):
    """Distribution summary after classification."""

    total_orders: int = Field(..., ge=0)
    p1_count: int = Field(..., ge=0)
    p2_count: int = Field(..., ge=0)
    p3_count: int = Field(..., ge=0)
    p1_total_value: float = Field(..., ge=0.0)
    p2_total_value: float = Field(..., ge=0.0)
    p3_total_value: float = Field(..., ge=0.0)
    primary_driver: str
    summary_text: str


class OrderTableRow(BaseModel):
    """Subset of ScoredOrder for table presentation."""

    order_id: str
    product_family: str
    customer_name: str
    customer_tier: str
    due_date: str
    quantity: int
    order_value: float
    weighted_score: float


class PriorityGroupTable(BaseModel):
    """Grouped table for a single priority level."""

    priority: str = Field(..., pattern=r"^(P1|P2|P3)$")
    orders: list[OrderTableRow]
    subtotal_quantity: int = Field(..., ge=0)
    subtotal_value: float = Field(..., ge=0.0)


class OrderExplanation(BaseModel):
    """Per-order classification explanation."""

    order_id: str
    weighted_score: float
    priority: str
    scores: CriterionScores
    weights_used: ScoringWeights
    explanation_text: str


# ---------------------------------------------------------------------------
# Reclassification
# ---------------------------------------------------------------------------

class ReclassifyInput(BaseModel):
    """Input for Planner-initiated priority override."""

    order_id: str = Field(..., pattern=r"^PO-\d{4}-\d{3}$")
    new_priority: str = Field(..., pattern=r"^(P1|P2|P3)$")


class ReclassificationResult(BaseModel):
    """Result of a reclassification operation."""

    overridden_order: ScoredOrder
    reevaluated_orders: list[ScoredOrder]
    updated_summary: PrioritySummary


# ---------------------------------------------------------------------------
# Audit
# ---------------------------------------------------------------------------

class ClassificationAuditEntry(BaseModel):
    """Audit entry for classification decisions."""

    session_id: str
    agent: str = "impact_assessment_agent"
    action: str = Field(
        ...,
        pattern=r"^(priority_classification|priority_reclassification|priority_reevaluation)$",
    )
    timestamp: str
    details: dict


# ---------------------------------------------------------------------------
# Shared Context (AgentCore Memory)
# ---------------------------------------------------------------------------

class SharedOrderEntry(BaseModel):
    """Per-order entry written to shared context."""

    order_id: str
    priority: str
    weighted_score: float
    scores: CriterionScores
    manually_classified: bool
    due_date: str
    product_family: str
    quantity: int
    order_value: float
    machine_types_required: list[str]
    customer_id: str
    customer_tier: str
    rolling_mill_hours: float
    finishing_line_hours: float
    raw_material_tons: float


class SharedPrioritizedOrders(BaseModel):
    """Full shared context payload written to AgentCore Memory."""

    session_id: str
    classified_at: str
    weights: ScoringWeights
    thresholds: PriorityThresholds
    summary: PrioritySummary
    orders: list[SharedOrderEntry]


# ---------------------------------------------------------------------------
# Structured Output (Strands structured_output_model)
# ---------------------------------------------------------------------------


class ImpactAssessmentOutput(BaseModel):
    """Structured output for Impact Assessment Agent.

    Used as structured_output_model in Agent() constructor.
    Contains scored orders, priority summary, and total value
    needed by the orchestrator to build the Round 1 UI payload.
    """

    scored_orders: list[ScoredOrder]
    priority_summary: PrioritySummary
    total_value: float = Field(0.0, ge=0.0)
    summary_text: str = ""
