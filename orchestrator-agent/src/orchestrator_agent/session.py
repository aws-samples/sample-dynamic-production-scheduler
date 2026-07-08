"""Workflow session state management.

Hybrid session state (Pattern 3): Strands conversation history holds
LLM context; this module tracks programmatic state (phase, decisions,
errors) in a WorkflowSession dataclass.
"""

from __future__ import annotations

import logging
import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any

from orchestrator_agent.models.schemas import (
    AgentError,
    DisruptionEvent,
    OrderDecision,
    WorkflowPhase,
)

logger = logging.getLogger("orchestrator_agent")

# Valid phase transitions (from -> set of allowed targets)
_VALID_TRANSITIONS: dict[WorkflowPhase, set[WorkflowPhase]] = {
    WorkflowPhase.IDLE: {WorkflowPhase.DISRUPTION_DETECTED},
    WorkflowPhase.DISRUPTION_DETECTED: {
        WorkflowPhase.ROUND1_IN_PROGRESS,
    },
    WorkflowPhase.ROUND1_IN_PROGRESS: {
        WorkflowPhase.ROUND1_COMPLETE,
    },
    WorkflowPhase.ROUND1_COMPLETE: {
        WorkflowPhase.ROUND2_DELAYS,
        WorkflowPhase.WHAT_IF,
    },
    WorkflowPhase.ROUND2_DELAYS: {
        WorkflowPhase.ROUND2_FUNNEL,
        WorkflowPhase.WHAT_IF,
    },
    WorkflowPhase.ROUND2_FUNNEL: {
        WorkflowPhase.SUMMARY,
        WorkflowPhase.WHAT_IF,
    },
    WorkflowPhase.WHAT_IF: {
        WorkflowPhase.ROUND1_COMPLETE,
        WorkflowPhase.ROUND2_DELAYS,
        WorkflowPhase.ROUND2_FUNNEL,
    },
    WorkflowPhase.SUMMARY: {WorkflowPhase.COMPLETE},
    WorkflowPhase.COMPLETE: set(),
}


@dataclass
class WorkflowSession:
    """Mutable session state for a single disruption workflow."""

    session_id: str = ""
    created_at: str = ""
    current_phase: WorkflowPhase = WorkflowPhase.IDLE
    disruption_event: DisruptionEvent | None = None
    round1_complete: bool = False
    round2_complete: bool = False
    decisions: list[OrderDecision] = field(default_factory=list)
    what_if_count: int = 0
    error_log: list[AgentError] = field(default_factory=list)

    def __post_init__(self) -> None:
        if not self.session_id:
            self.session_id = str(uuid.uuid4())
        if not self.created_at:
            self.created_at = datetime.now(timezone.utc).isoformat()

    # -- Phase transitions --

    def transition(self, new_phase: WorkflowPhase) -> None:
        """Transition to a new workflow phase.

        Raises ValueError if the transition is not valid per the
        state machine defined in domain-entities.md.
        """
        allowed = _VALID_TRANSITIONS.get(self.current_phase, set())
        if new_phase not in allowed:
            raise ValueError(
                f"Invalid transition: {self.current_phase.value}"
                f" -> {new_phase.value}"
            )
        old = self.current_phase
        self.current_phase = new_phase

        if new_phase == WorkflowPhase.ROUND1_COMPLETE:
            self.round1_complete = True
        elif new_phase == WorkflowPhase.SUMMARY:
            self.round2_complete = True
        elif new_phase == WorkflowPhase.WHAT_IF:
            self.what_if_count += 1

        logger.info(
            "Phase transition",
            extra={"old_phase": old.value, "new_phase": new_phase.value},
        )

    # -- Record helpers --

    def record_decision(self, decision: OrderDecision) -> None:
        """Append an order decision to the session."""
        self.decisions.append(decision)
        logger.info(
            "Decision recorded",
            extra={
                "order_id": decision.order_id,
                "type": decision.decision_type,
            },
        )

    def record_error(self, error: AgentError) -> None:
        """Append an agent error to the session."""
        self.error_log.append(error)
        logger.warning(
            "Agent error recorded",
            extra={
                "agent_id": error.agent_id,
                "error_type": error.error_type,
            },
        )

    # -- Serialization --

    def to_dict(self) -> dict[str, Any]:
        """Serialize session to a plain dict for persistence."""
        d = asdict(self)
        d["current_phase"] = self.current_phase.value
        return d

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "WorkflowSession":
        """Restore session from a persisted dict."""
        phase_val = data.pop("current_phase", "idle")
        phase = WorkflowPhase(phase_val)

        disruption_raw = data.pop("disruption_event", None)
        disruption = (
            DisruptionEvent(**disruption_raw)
            if disruption_raw
            else None
        )

        decisions_raw = data.pop("decisions", [])
        decisions = [OrderDecision(**d) for d in decisions_raw]

        errors_raw = data.pop("error_log", [])
        errors = [AgentError(**e) for e in errors_raw]

        return cls(
            session_id=data.get("session_id", ""),
            created_at=data.get("created_at", ""),
            current_phase=phase,
            disruption_event=disruption,
            round1_complete=data.get("round1_complete", False),
            round2_complete=data.get("round2_complete", False),
            decisions=decisions,
            what_if_count=data.get("what_if_count", 0),
            error_log=errors,
        )


def create_session() -> WorkflowSession:
    """Create a new workflow session with a fresh UUID."""
    session = WorkflowSession()
    logger.info(
        "Session created",
        extra={"session_id": session.session_id},
    )
    return session
