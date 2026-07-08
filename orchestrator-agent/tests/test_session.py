"""Tests for Orchestrator Agent session management."""

from __future__ import annotations

import pytest

from orchestrator_agent.models.schemas import (
    AgentError,
    OrderDecision,
    WorkflowPhase,
)
from orchestrator_agent.session import WorkflowSession, create_session


class TestCreateSession:
    def test_creates_with_uuid(self):
        s = create_session()
        assert len(s.session_id) == 36
        assert "-" in s.session_id

    def test_starts_idle(self):
        s = create_session()
        assert s.current_phase == WorkflowPhase.IDLE

    def test_empty_collections(self):
        s = create_session()
        assert s.decisions == []
        assert s.error_log == []
        assert s.what_if_count == 0


class TestPhaseTransitions:
    def test_valid_full_workflow(self):
        s = create_session()
        s.transition(WorkflowPhase.DISRUPTION_DETECTED)
        s.transition(WorkflowPhase.ROUND1_IN_PROGRESS)
        s.transition(WorkflowPhase.ROUND1_COMPLETE)
        assert s.round1_complete is True
        s.transition(WorkflowPhase.ROUND2_DELAYS)
        s.transition(WorkflowPhase.ROUND2_FUNNEL)
        s.transition(WorkflowPhase.SUMMARY)
        assert s.round2_complete is True
        s.transition(WorkflowPhase.COMPLETE)
        assert s.current_phase == WorkflowPhase.COMPLETE

    def test_invalid_transition_raises(self):
        s = create_session()
        with pytest.raises(ValueError, match="Invalid transition"):
            s.transition(WorkflowPhase.ROUND1_COMPLETE)

    def test_cannot_leave_complete(self):
        s = create_session()
        s.transition(WorkflowPhase.DISRUPTION_DETECTED)
        s.transition(WorkflowPhase.ROUND1_IN_PROGRESS)
        s.transition(WorkflowPhase.ROUND1_COMPLETE)
        s.transition(WorkflowPhase.ROUND2_DELAYS)
        s.transition(WorkflowPhase.ROUND2_FUNNEL)
        s.transition(WorkflowPhase.SUMMARY)
        s.transition(WorkflowPhase.COMPLETE)
        with pytest.raises(ValueError):
            s.transition(WorkflowPhase.IDLE)

    def test_what_if_from_round1_complete(self):
        s = create_session()
        s.transition(WorkflowPhase.DISRUPTION_DETECTED)
        s.transition(WorkflowPhase.ROUND1_IN_PROGRESS)
        s.transition(WorkflowPhase.ROUND1_COMPLETE)
        s.transition(WorkflowPhase.WHAT_IF)
        assert s.what_if_count == 1
        s.transition(WorkflowPhase.ROUND1_COMPLETE)
        assert s.current_phase == WorkflowPhase.ROUND1_COMPLETE

    def test_what_if_from_round2_delays(self):
        s = create_session()
        s.transition(WorkflowPhase.DISRUPTION_DETECTED)
        s.transition(WorkflowPhase.ROUND1_IN_PROGRESS)
        s.transition(WorkflowPhase.ROUND1_COMPLETE)
        s.transition(WorkflowPhase.ROUND2_DELAYS)
        s.transition(WorkflowPhase.WHAT_IF)
        assert s.what_if_count == 1
        s.transition(WorkflowPhase.ROUND2_DELAYS)

    def test_what_if_from_round2_funnel(self):
        s = create_session()
        s.transition(WorkflowPhase.DISRUPTION_DETECTED)
        s.transition(WorkflowPhase.ROUND1_IN_PROGRESS)
        s.transition(WorkflowPhase.ROUND1_COMPLETE)
        s.transition(WorkflowPhase.ROUND2_DELAYS)
        s.transition(WorkflowPhase.ROUND2_FUNNEL)
        s.transition(WorkflowPhase.WHAT_IF)
        s.transition(WorkflowPhase.ROUND2_FUNNEL)
        assert s.what_if_count == 1

    def test_multiple_what_ifs(self):
        s = create_session()
        s.transition(WorkflowPhase.DISRUPTION_DETECTED)
        s.transition(WorkflowPhase.ROUND1_IN_PROGRESS)
        s.transition(WorkflowPhase.ROUND1_COMPLETE)
        s.transition(WorkflowPhase.WHAT_IF)
        s.transition(WorkflowPhase.ROUND1_COMPLETE)
        s.transition(WorkflowPhase.WHAT_IF)
        s.transition(WorkflowPhase.ROUND1_COMPLETE)
        assert s.what_if_count == 2


class TestRecordDecision:
    def test_append_decision(self):
        s = create_session()
        d = OrderDecision(
            order_id="PO-001",
            decision_type="delay_approval",
            agent_source="capacity_optimization",
            round=2,
        )
        s.record_decision(d)
        assert len(s.decisions) == 1
        assert s.decisions[0].order_id == "PO-001"


class TestRecordError:
    def test_append_error(self):
        s = create_session()
        e = AgentError(
            agent_id="agent-123",
            error_type="timeout",
            message="Timed out",
        )
        s.record_error(e)
        assert len(s.error_log) == 1
        assert s.error_log[0].error_type == "timeout"


class TestSerialization:
    def test_round_trip(self):
        s = create_session()
        s.transition(WorkflowPhase.DISRUPTION_DETECTED)
        s.transition(WorkflowPhase.ROUND1_IN_PROGRESS)
        s.transition(WorkflowPhase.ROUND1_COMPLETE)
        s.record_decision(OrderDecision(
            order_id="PO-001",
            decision_type="reroute_approve",
            agent_source="constraint_matching",
            round=2,
        ))
        s.record_error(AgentError(
            agent_id="agent-x",
            error_type="exception",
            message="boom",
        ))

        data = s.to_dict()
        restored = WorkflowSession.from_dict(data)

        assert restored.session_id == s.session_id
        assert restored.current_phase == WorkflowPhase.ROUND1_COMPLETE
        assert restored.round1_complete is True
        assert len(restored.decisions) == 1
        assert restored.decisions[0].order_id == "PO-001"
        assert len(restored.error_log) == 1
        assert restored.error_log[0].agent_id == "agent-x"

    def test_from_dict_defaults(self):
        data = {"session_id": "test-123", "created_at": "2026-01-01"}
        restored = WorkflowSession.from_dict(data)
        assert restored.current_phase == WorkflowPhase.IDLE
        assert restored.disruption_event is None
        assert restored.decisions == []

    def test_to_dict_phase_is_string(self):
        s = create_session()
        d = s.to_dict()
        assert d["current_phase"] == "idle"
        assert isinstance(d["current_phase"], str)
