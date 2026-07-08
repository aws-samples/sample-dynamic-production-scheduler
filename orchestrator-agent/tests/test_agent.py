"""Tests for Orchestrator Agent — tools, factory, and wrapper."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any
from unittest.mock import MagicMock, patch

import pytest

from orchestrator_agent.config import OrchestratorSettings
from orchestrator_agent.models.schemas import AgentResult, WorkflowPhase
from orchestrator_agent.session import create_session
import orchestrator_agent.agent as agent_mod


# -------------------------------------------------------------------
# Fixtures
# -------------------------------------------------------------------

def _valid_settings() -> OrchestratorSettings:
    return OrchestratorSettings(
        impact_assessment_agent_arn="arn:aws:bedrock-agentcore:us-east-1:123456789012:runtime/impact_assessment_agent-FNJvbQBqOl",
        capacity_optimization_agent_arn="arn:aws:bedrock-agentcore:us-east-1:123456789012:runtime/capacity_optimization_agent-hdKAx3DZJX",
        constraint_matching_agent_arn="arn:aws:bedrock-agentcore:us-east-1:123456789012:runtime/constraint_matching_agent-EuLExyBsv5",
        gateway_url="https://gateway",
    )


@dataclass
class FakeAgentResponse:
    output_text: str


class FakeAgentCoreClient:
    """Mock AgentCore client for sub-agent invocation tests."""

    def __init__(self, responses: dict[str, str] | None = None,
                 fail_arns: set[str] | None = None):
        self.responses = responses or {}
        self.fail_arns = fail_arns or set()
        self.calls: list[dict[str, Any]] = []

    def invoke_agent(self, agent_arn: str, input_text: str,
                     session_id: str) -> FakeAgentResponse:
        self.calls.append({
            "agent_arn": agent_arn,
            "input_text": input_text,
            "session_id": session_id,
        })
        if agent_arn in self.fail_arns:
            raise RuntimeError(f"Agent {agent_arn} unavailable")
        text = self.responses.get(agent_arn, "default response")
        return FakeAgentResponse(output_text=text)


def _setup_module_state(
    settings: OrchestratorSettings | None = None,
    client: Any = None,
) -> None:
    """Set module-level state for tool tests."""
    agent_mod._settings = settings or _valid_settings()
    agent_mod._session = create_session()
    agent_mod._agentcore_client = client


# -------------------------------------------------------------------
# Sub-agent tool tests
# -------------------------------------------------------------------

class TestInvokeImpactAssessment:
    def test_success(self):
        client = FakeAgentCoreClient(
            responses={"arn:aws:bedrock-agentcore:us-east-1:123456789012:runtime/impact_assessment_agent-FNJvbQBqOl": "P1: 5 orders, P2: 3 orders"}
        )
        _setup_module_state(client=client)
        result = agent_mod.invoke_impact_assessment.__wrapped__(
            prompt="Analyze Florida orders"
        )
        assert "P1" in result
        assert len(client.calls) == 1

    def test_retry_on_failure(self):
        """First call fails, retry succeeds."""
        call_count = 0
        original_settings = _valid_settings()

        class RetryClient:
            def invoke_agent(self, **kwargs):
                nonlocal call_count
                call_count += 1
                if call_count == 1:
                    raise RuntimeError("transient error")
                return FakeAgentResponse(output_text="recovered")

        _setup_module_state(settings=original_settings,
                           client=RetryClient())
        result = agent_mod.invoke_impact_assessment.__wrapped__(
            prompt="Analyze"
        )
        assert "recovered" in result
        assert call_count == 2

    def test_permanent_failure(self):
        client = FakeAgentCoreClient(fail_arns={"arn:aws:bedrock-agentcore:us-east-1:123456789012:runtime/impact_assessment_agent-FNJvbQBqOl"})
        _setup_module_state(client=client)
        result = agent_mod.invoke_impact_assessment.__wrapped__(
            prompt="Analyze"
        )
        assert "unavailable" in result.lower()
        assert len(agent_mod._session.error_log) == 1


class TestInvokeCapacityOptimization:
    def test_success(self):
        client = FakeAgentCoreClient(
            responses={"arn:aws:bedrock-agentcore:us-east-1:123456789012:runtime/capacity_optimization_agent-hdKAx3DZJX": "Capacity: 72% utilized"}
        )
        _setup_module_state(client=client)
        result = agent_mod.invoke_capacity_optimization.__wrapped__(
            prompt="Analyze Ohio capacity"
        )
        assert "72%" in result

    def test_permanent_failure(self):
        client = FakeAgentCoreClient(fail_arns={"arn:aws:bedrock-agentcore:us-east-1:123456789012:runtime/capacity_optimization_agent-hdKAx3DZJX"})
        _setup_module_state(client=client)
        result = agent_mod.invoke_capacity_optimization.__wrapped__(
            prompt="Analyze"
        )
        assert "unavailable" in result.lower()


class TestInvokeConstraintMatching:
    def test_success(self):
        client = FakeAgentCoreClient(
            responses={"arn:aws:bedrock-agentcore:us-east-1:123456789012:runtime/constraint_matching_agent-EuLExyBsv5": "Funnel complete: 8 orders matched"}
        )
        _setup_module_state(client=client)
        result = agent_mod.invoke_constraint_matching.__wrapped__(
            prompt="Run funnel"
        )
        assert "8 orders" in result

    def test_permanent_failure(self):
        client = FakeAgentCoreClient(fail_arns={"arn:aws:bedrock-agentcore:us-east-1:123456789012:runtime/constraint_matching_agent-EuLExyBsv5"})
        _setup_module_state(client=client)
        result = agent_mod.invoke_constraint_matching.__wrapped__(
            prompt="Run funnel"
        )
        assert "unavailable" in result.lower()


# -------------------------------------------------------------------
# Session tool tests
# -------------------------------------------------------------------

class TestGetSessionState:
    def test_returns_json(self):
        _setup_module_state()
        result = agent_mod.get_session_state.__wrapped__()
        assert '"current_phase"' in result
        assert '"idle"' in result


class TestUpdateSessionPhase:
    def test_valid_transition(self):
        _setup_module_state()
        result = agent_mod.update_session_phase.__wrapped__(
            new_phase="disruption_detected"
        )
        assert "updated" in result.lower()
        assert agent_mod._session.current_phase == (
            WorkflowPhase.DISRUPTION_DETECTED
        )

    def test_invalid_transition(self):
        _setup_module_state()
        result = agent_mod.update_session_phase.__wrapped__(
            new_phase="complete"
        )
        assert "invalid" in result.lower()

    def test_invalid_phase_name(self):
        _setup_module_state()
        result = agent_mod.update_session_phase.__wrapped__(
            new_phase="nonexistent"
        )
        assert "invalid" in result.lower()


# -------------------------------------------------------------------
# run_agent wrapper tests
# -------------------------------------------------------------------

class TestRunAgent:
    def test_success(self):
        mock_agent = MagicMock(return_value="workflow complete")
        _setup_module_state()
        result = agent_mod.run_agent(
            mock_agent, "Start disruption workflow", "session-123"
        )
        assert result.success is True
        assert result.data == "workflow complete"
        mock_agent.assert_called_once_with("Start disruption workflow")

    def test_exception_returns_error(self):
        mock_agent = MagicMock(side_effect=RuntimeError("LLM error"))
        _setup_module_state()
        result = agent_mod.run_agent(
            mock_agent, "Start workflow", "session-123"
        )
        assert result.success is False
        assert "error" in result.error.lower()

    def test_keyboard_interrupt(self):
        mock_agent = MagicMock(side_effect=KeyboardInterrupt)
        _setup_module_state()
        result = agent_mod.run_agent(
            mock_agent, "Start workflow", "session-123"
        )
        assert result.success is False
        assert "interrupted" in result.error.lower()


# -------------------------------------------------------------------
# create_agent initialization test
# -------------------------------------------------------------------

class TestCreateAgent:
    @patch("orchestrator_agent.agent._get_or_create_mcp_client_cached")
    @patch("orchestrator_agent.agent.Agent")
    @patch("orchestrator_agent.agent.BedrockModel")
    def test_creates_agent(self, mock_model_cls, mock_agent_cls,
                           mock_mcp_factory):
        mock_mcp_factory.return_value = (MagicMock(), [])
        mock_model_cls.return_value = MagicMock()
        mock_agent_cls.return_value = MagicMock()

        settings = _valid_settings()
        agent = agent_mod.create_agent(
            settings=settings,
            agentcore_client=MagicMock(),
        )

        mock_model_cls.assert_called_once()
        mock_agent_cls.assert_called_once()
        assert agent_mod._settings is settings
        assert agent_mod._session is not None
        assert agent_mod._session.current_phase == WorkflowPhase.IDLE


# -------------------------------------------------------------------
# Session cache tests (Phase 1 looping fix)
# -------------------------------------------------------------------

class TestSessionCache:
    """Verify that create_agent reuses cached sessions so workflow
    phase state survives across per-request Agent creation."""

    def setup_method(self):
        """Clear the module-level session cache before each test."""
        agent_mod._session_cache.clear()

    @patch("orchestrator_agent.agent._get_or_create_mcp_client_cached")
    @patch("orchestrator_agent.agent.Agent")
    @patch("orchestrator_agent.agent.BedrockModel")
    def test_same_session_id_reuses_session(
        self, mock_model_cls, mock_agent_cls, mock_mcp_factory
    ):
        """Calling create_agent twice with the same session_id should
        reuse the WorkflowSession — phase transitions persist."""
        mock_mcp_factory.return_value = (MagicMock(), [])
        mock_model_cls.return_value = MagicMock()
        mock_agent_cls.return_value = MagicMock()

        settings = _valid_settings()
        sid = "test-session-reuse"

        # First call — creates a new session at IDLE
        agent_mod.create_agent(
            settings=settings,
            agentcore_client=MagicMock(),
            session_id=sid,
        )
        assert agent_mod._session.current_phase == WorkflowPhase.IDLE

        # Advance the phase to DISRUPTION_DETECTED
        agent_mod._session.transition(WorkflowPhase.DISRUPTION_DETECTED)
        assert agent_mod._session.current_phase == WorkflowPhase.DISRUPTION_DETECTED

        # Second call with same session_id — should reuse, NOT reset
        agent_mod.create_agent(
            settings=settings,
            agentcore_client=MagicMock(),
            session_id=sid,
        )
        assert agent_mod._session.current_phase == WorkflowPhase.DISRUPTION_DETECTED

    @patch("orchestrator_agent.agent._get_or_create_mcp_client_cached")
    @patch("orchestrator_agent.agent.Agent")
    @patch("orchestrator_agent.agent.BedrockModel")
    def test_different_session_id_creates_new_session(
        self, mock_model_cls, mock_agent_cls, mock_mcp_factory
    ):
        """Different session_ids should get independent sessions."""
        mock_mcp_factory.return_value = (MagicMock(), [])
        mock_model_cls.return_value = MagicMock()
        mock_agent_cls.return_value = MagicMock()

        settings = _valid_settings()

        agent_mod.create_agent(
            settings=settings,
            agentcore_client=MagicMock(),
            session_id="session-A",
        )
        agent_mod._session.transition(WorkflowPhase.DISRUPTION_DETECTED)

        # New session_id — should start fresh at IDLE
        agent_mod.create_agent(
            settings=settings,
            agentcore_client=MagicMock(),
            session_id="session-B",
        )
        assert agent_mod._session.current_phase == WorkflowPhase.IDLE

        # Original session-A should still be cached at DISRUPTION_DETECTED
        assert agent_mod._session_cache["session-A"].current_phase == WorkflowPhase.DISRUPTION_DETECTED

    @patch("orchestrator_agent.agent._get_or_create_mcp_client_cached")
    @patch("orchestrator_agent.agent.Agent")
    @patch("orchestrator_agent.agent.BedrockModel")
    def test_lru_eviction(
        self, mock_model_cls, mock_agent_cls, mock_mcp_factory
    ):
        """Cache should evict oldest entry when exceeding _MAX_SESSION_CACHE."""
        mock_mcp_factory.return_value = (MagicMock(), [])
        mock_model_cls.return_value = MagicMock()
        mock_agent_cls.return_value = MagicMock()

        settings = _valid_settings()
        original_max = agent_mod._MAX_SESSION_CACHE

        try:
            # Temporarily lower the limit for testing
            agent_mod._MAX_SESSION_CACHE = 3

            for i in range(4):
                agent_mod.create_agent(
                    settings=settings,
                    agentcore_client=MagicMock(),
                    session_id=f"evict-{i}",
                )

            # First session should have been evicted
            assert "evict-0" not in agent_mod._session_cache
            # Later sessions should still be cached
            assert "evict-1" in agent_mod._session_cache
            assert "evict-2" in agent_mod._session_cache
            assert "evict-3" in agent_mod._session_cache
        finally:
            agent_mod._MAX_SESSION_CACHE = original_max

    @patch("orchestrator_agent.agent._get_or_create_mcp_client_cached")
    @patch("orchestrator_agent.agent.Agent")
    @patch("orchestrator_agent.agent.BedrockModel")
    def test_no_session_id_skips_cache(
        self, mock_model_cls, mock_agent_cls, mock_mcp_factory
    ):
        """Empty session_id should create a fresh session without caching."""
        mock_mcp_factory.return_value = (MagicMock(), [])
        mock_model_cls.return_value = MagicMock()
        mock_agent_cls.return_value = MagicMock()

        settings = _valid_settings()
        cache_size_before = len(agent_mod._session_cache)

        agent_mod.create_agent(
            settings=settings,
            agentcore_client=MagicMock(),
            session_id="",
        )

        assert len(agent_mod._session_cache) == cache_size_before
        assert agent_mod._session.current_phase == WorkflowPhase.IDLE


