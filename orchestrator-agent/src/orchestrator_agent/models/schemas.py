"""Pydantic schema models for the Orchestrator Agent.

All domain entities from domain-entities.md — WorkflowPhase enum,
session state, disruption events, sub-agent request/response,
order decisions, errors, streaming, audit, and input validation.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field, field_validator


# -------------------------------------------------------------------
# Enums
# -------------------------------------------------------------------

class WorkflowPhase(str, Enum):
    """Workflow state machine phases."""

    IDLE = "idle"
    DISRUPTION_DETECTED = "disruption_detected"
    ROUND1_IN_PROGRESS = "round1_in_progress"
    ROUND1_COMPLETE = "round1_complete"
    ROUND2_DELAYS = "round2_delays"
    ROUND2_FUNNEL = "round2_funnel"
    WHAT_IF = "what_if"
    SUMMARY = "summary"
    COMPLETE = "complete"


# -------------------------------------------------------------------
# Session state (dataclass — mutable, used programmatically)
# -------------------------------------------------------------------

@dataclass
class DisruptionEvent:
    """Trigger event for the disruption workflow."""

    event_type: str
    affected_plant: str
    description: str
    detected_at: str = ""
    severity: str | None = None

    def __post_init__(self) -> None:
        if not self.detected_at:
            self.detected_at = datetime.now(timezone.utc).isoformat()


@dataclass
class OrderDecision:
    """Tracks a single Planner decision during the workflow."""

    order_id: str
    decision_type: str  # delay_approval | delay_rejection | reroute_approve | reroute_reject | reroute_skip
    agent_source: str   # capacity_optimization | constraint_matching
    round: int
    timestamp: str = ""
    details: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.timestamp:
            self.timestamp = datetime.now(timezone.utc).isoformat()


@dataclass
class AgentError:
    """Records a sub-agent failure."""

    agent_id: str
    error_type: str  # timeout | exception | invalid_response
    message: str
    timestamp: str = ""
    retried: bool = False
    retry_succeeded: bool | None = None

    def __post_init__(self) -> None:
        if not self.timestamp:
            self.timestamp = datetime.now(timezone.utc).isoformat()


# -------------------------------------------------------------------
# Sub-agent invocation
# -------------------------------------------------------------------

@dataclass
class SubAgentRequest:
    """Request payload for an AgentCore sub-agent invocation."""

    agent_id: str
    input_text: str
    session_id: str


@dataclass
class SubAgentResponse:
    """Response from an AgentCore sub-agent invocation."""

    agent_id: str
    output_text: str
    success: bool
    error_message: str | None = None
    duration_ms: int = 0


# -------------------------------------------------------------------
# Streaming
# -------------------------------------------------------------------

@dataclass
class StreamToken:
    """A single streaming token from a sub-agent."""

    token: str
    agent_name: str
    token_type: str = "text"  # text | structured_data


@dataclass
class StructuredPayload:
    """A complete structured data block for frontend rendering."""

    payload_type: str  # table | tracker | summary | approval_request
    data: dict[str, Any] = field(default_factory=dict)
    agent_name: str = ""


# -------------------------------------------------------------------
# Audit
# -------------------------------------------------------------------

@dataclass
class OrchestratorAuditEntry:
    """Audit entry for workflow-level events written to Audit MCP."""

    session_id: str
    agent: str = "orchestrator_agent"
    action: str = ""
    timestamp: str = ""
    details: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.timestamp:
            self.timestamp = datetime.now(timezone.utc).isoformat()


# -------------------------------------------------------------------
# Input validation (Pattern 6 — SECURITY-05)
# -------------------------------------------------------------------

MAX_MESSAGE_LENGTH = 4000


class PlannerMessage(BaseModel):
    """Validated Planner input message.

    Enforces max length, non-empty, and basic sanitization.
    """

    text: str = Field(..., max_length=MAX_MESSAGE_LENGTH)
    session_id: str = Field(..., pattern=r"^[0-9a-f\-]{36}$")

    @field_validator("text")
    @classmethod
    def sanitize_text(cls, v: str) -> str:
        """Reject empty messages and strip script tags."""
        if not v.strip():
            raise ValueError("Message cannot be empty")
        return re.sub(
            r"<script[^>]*>.*?</script>", "", v, flags=re.IGNORECASE | re.DOTALL
        )


# -------------------------------------------------------------------
# UI Payload — structured data for frontend rendering (Rework 6)
# -------------------------------------------------------------------

class UiAgentStatus(BaseModel):
    """Status of a sub-agent during workflow execution."""
    name: str
    status: str  # idle | running | complete | error
    summary: str | None = None

class UiOrder(BaseModel):
    """Order data for frontend table rendering."""
    orderId: str
    product: str = ""
    customer: str = ""
    customerTier: str = ""
    value: str = ""
    dueDate: str = ""
    priority: str = ""
    risk: str = ""
    slack: str = ""
    rmHrs: str = ""
    flHrs: str = ""

class UiCapacity(BaseModel):
    """Capacity snapshot for frontend gauges."""
    rollingMill: float | None = None
    finishingLine: float | None = None
    rawMaterial: float | None = None
    workforce: float | None = None
    overall: float | None = None

class UiPriorities(BaseModel):
    """Priority distribution counts."""
    P1: int = 0
    P2: int = 0
    P3: int = 0
    P1Value: str = ""
    P2Value: str = ""
    P3Value: str = ""

class UiApprovalOption(BaseModel):
    """A single decision option for an approval request."""
    label: str
    key: str
    hint: str = ""

class UiApprovalRequest(BaseModel):
    """Single order decision request for the frontend."""
    orderId: str
    product: str = ""
    customer: str = ""
    customerTier: str = ""
    value: str = ""
    recommendation: str = ""
    options: list[UiApprovalOption] = []
    funnelResults: list[dict[str, Any]] = Field(default_factory=list)
    reasoning: str = ""

class UiCapacityImpactDimension(BaseModel):
    """Current and projected utilization for a single capacity dimension."""
    current: float = 0.0
    projected: float = 0.0

class UiCapacityImpactPlant(BaseModel):
    """Capacity impact data for a single plant."""
    name: str
    rollingMill: UiCapacityImpactDimension = Field(default_factory=UiCapacityImpactDimension)
    finishingLine: UiCapacityImpactDimension = Field(default_factory=UiCapacityImpactDimension)
    overall: UiCapacityImpactDimension = Field(default_factory=UiCapacityImpactDimension)

class UiCapacityImpact(BaseModel):
    """Live capacity impact for both plants during disruption workflow."""
    senderPlant: UiCapacityImpactPlant
    receiverPlant: UiCapacityImpactPlant

class UiTransferOrder(BaseModel):
    """Order approved for transfer from constraint funnel."""
    orderId: str
    product: str = ""
    customer: str = ""
    customerTier: str = ""
    value: str = ""
    dueDate: str = ""
    priority: str = ""
    recommendation: str = ""
    reasoning: str = ""
    funnelResults: list[dict[str, Any]] = Field(default_factory=list)

class UiPayload(BaseModel):
    """Top-level structured UI payload sent to the frontend.
    
    Built deterministically by the orchestrator's agentcore_server from
    sub-agent structured outputs. Fields are all optional — only include
    what's relevant for the current phase.
    """
    phase: str | None = None
    agents: list[UiAgentStatus] | None = None
    orders: list[UiOrder] | None = None
    capacity: UiCapacity | None = None
    priorities: UiPriorities | None = None
    approvalRequest: UiApprovalRequest | None = None
    totalOrders: int | None = None
    totalValue: str | None = None
    bottleneck: str | None = None
    complete: bool | None = None
    capacityImpact: UiCapacityImpact | None = None
    transferOrders: list[UiTransferOrder] | None = None


# -------------------------------------------------------------------
# Agent result wrapper
# -------------------------------------------------------------------

@dataclass
class AgentResult:
    """Wrapper for agent invocation results (Pattern 7)."""

    success: bool
    data: Any = None
    error: str | None = None
