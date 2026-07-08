"""Tests for Orchestrator Agent schema models."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from orchestrator_agent.models.schemas import (
    AgentError,
    AgentResult,
    DisruptionEvent,
    OrchestratorAuditEntry,
    OrderDecision,
    PlannerMessage,
    StreamToken,
    StructuredPayload,
    SubAgentRequest,
    SubAgentResponse,
    WorkflowPhase,
)


# -------------------------------------------------------------------
# WorkflowPhase
# -------------------------------------------------------------------

class TestWorkflowPhase:
    def test_all_phases_exist(self):
        phases = [p.value for p in WorkflowPhase]
        assert "idle" in phases
        assert "disruption_detected" in phases
        assert "round1_in_progress" in phases
        assert "round1_complete" in phases
        assert "round2_delays" in phases
        assert "round2_funnel" in phases
        assert "what_if" in phases
        assert "summary" in phases
        assert "complete" in phases

    def test_phase_count(self):
        assert len(WorkflowPhase) == 9

    def test_phase_is_string(self):
        assert WorkflowPhase.IDLE == "idle"


# -------------------------------------------------------------------
# PlannerMessage validation
# -------------------------------------------------------------------

class TestPlannerMessage:
    VALID_SESSION = "12345678-1234-1234-1234-123456789abc"

    def test_valid_message(self):
        msg = PlannerMessage(text="Hello", session_id=self.VALID_SESSION)
        assert msg.text == "Hello"

    def test_empty_message_rejected(self):
        with pytest.raises(ValidationError):
            PlannerMessage(text="   ", session_id=self.VALID_SESSION)

    def test_max_length_exceeded(self):
        with pytest.raises(ValidationError):
            PlannerMessage(text="x" * 4001, session_id=self.VALID_SESSION)

    def test_max_length_boundary(self):
        msg = PlannerMessage(text="x" * 4000, session_id=self.VALID_SESSION)
        assert len(msg.text) == 4000

    def test_script_tag_stripped(self):
        msg = PlannerMessage(
            text="Hello <script>alert(1)</script> world",
            session_id=self.VALID_SESSION,
        )
        assert "<script>" not in msg.text
        assert "Hello" in msg.text
        assert "world" in msg.text

    def test_invalid_session_id(self):
        with pytest.raises(ValidationError):
            PlannerMessage(text="Hello", session_id="not-a-uuid")


# -------------------------------------------------------------------
# DisruptionEvent
# -------------------------------------------------------------------

class TestDisruptionEvent:
    def test_auto_timestamp(self):
        evt = DisruptionEvent(
            event_type="tornado",
            affected_plant="Florida",
            description="Tornado approaching",
        )
        assert evt.detected_at != ""
        assert "T" in evt.detected_at

    def test_explicit_timestamp(self):
        evt = DisruptionEvent(
            event_type="flood",
            affected_plant="Florida",
            description="Flooding",
            detected_at="2026-01-01T00:00:00Z",
        )
        assert evt.detected_at == "2026-01-01T00:00:00Z"


# -------------------------------------------------------------------
# OrderDecision
# -------------------------------------------------------------------

class TestOrderDecision:
    def test_auto_timestamp(self):
        d = OrderDecision(
            order_id="PO-2026-001",
            decision_type="delay_approval",
            agent_source="capacity_optimization",
            round=2,
        )
        assert d.timestamp != ""

    def test_details_default_empty(self):
        d = OrderDecision(
            order_id="PO-2026-001",
            decision_type="reroute_approve",
            agent_source="constraint_matching",
            round=2,
        )
        assert d.details == {}


# -------------------------------------------------------------------
# AgentError
# -------------------------------------------------------------------

class TestAgentError:
    def test_auto_timestamp(self):
        err = AgentError(
            agent_id="agent-123",
            error_type="timeout",
            message="Timed out",
        )
        assert err.timestamp != ""
        assert err.retried is False

    def test_retry_fields(self):
        err = AgentError(
            agent_id="agent-123",
            error_type="exception",
            message="Boom",
            retried=True,
            retry_succeeded=False,
        )
        assert err.retried is True
        assert err.retry_succeeded is False


# -------------------------------------------------------------------
# Other dataclasses
# -------------------------------------------------------------------

class TestSubAgentModels:
    def test_request(self):
        req = SubAgentRequest(
            agent_id="a1", input_text="analyze", session_id="s1"
        )
        assert req.agent_id == "a1"

    def test_response_success(self):
        resp = SubAgentResponse(
            agent_id="a1", output_text="done", success=True
        )
        assert resp.success is True
        assert resp.error_message is None

    def test_response_failure(self):
        resp = SubAgentResponse(
            agent_id="a1", output_text="", success=False,
            error_message="timeout",
        )
        assert resp.success is False


class TestStreamingModels:
    def test_stream_token(self):
        t = StreamToken(token="hello", agent_name="impact")  # noqa: B105 B106 - test data, not a credential
        assert t.token_type == "text"

    def test_structured_payload(self):
        p = StructuredPayload(
            payload_type="table",
            data={"rows": []},
            agent_name="capacity",
        )
        assert p.payload_type == "table"


class TestAuditEntry:
    def test_auto_timestamp(self):
        entry = OrchestratorAuditEntry(
            session_id="s1", action="workflow_started"
        )
        assert entry.agent == "orchestrator_agent"
        assert entry.timestamp != ""


class TestAgentResult:
    def test_success(self):
        r = AgentResult(success=True, data="output")
        assert r.success is True
        assert r.error is None

    def test_failure(self):
        r = AgentResult(success=False, error="boom")
        assert r.success is False
        assert r.data is None
