"""Tests for Orchestrator Agent configuration."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from orchestrator_agent.config import OrchestratorSettings


def _valid_env() -> dict[str, str]:
    """Return minimal valid environment for OrchestratorSettings."""
    return {
        "impact_assessment_agent_arn": "arn:aws:bedrock-agentcore:us-east-1:123456789012:runtime/ia-test",
        "capacity_optimization_agent_arn": "arn:aws:bedrock-agentcore:us-east-1:123456789012:runtime/co-test",
        "constraint_matching_agent_arn": "arn:aws:bedrock-agentcore:us-east-1:123456789012:runtime/cm-test",
    }


class TestOrchestratorSettings:
    def test_valid_defaults(self):
        s = OrchestratorSettings(**_valid_env())
        assert s.bedrock_model_id.startswith("us.anthropic")
        assert s.session_timeout_minutes == 60
        assert s.max_turns == 100
        assert s.retry_limit == 1

    def test_env_override(self):
        env = _valid_env()
        env["session_timeout_minutes"] = "120"
        env["retry_limit"] = "3"
        s = OrchestratorSettings(**env)
        assert s.session_timeout_minutes == 120
        assert s.retry_limit == 3

    def test_empty_impact_agent_id_rejected(self):
        env = _valid_env()
        env["impact_assessment_agent_arn"] = ""
        with pytest.raises(ValidationError, match="impact_assessment"):
            OrchestratorSettings(**env)

    def test_empty_capacity_agent_id_rejected(self):
        env = _valid_env()
        env["capacity_optimization_agent_arn"] = ""
        with pytest.raises(ValidationError, match="capacity_optimization"):
            OrchestratorSettings(**env)

    def test_empty_constraint_agent_id_rejected(self):
        env = _valid_env()
        env["constraint_matching_agent_arn"] = ""
        with pytest.raises(ValidationError, match="constraint_matching"):
            OrchestratorSettings(**env)

    def test_invalid_timeout_rejected(self):
        env = _valid_env()
        env["session_timeout_minutes"] = "0"
        with pytest.raises(ValidationError, match="session_timeout"):
            OrchestratorSettings(**env)

    def test_negative_retry_rejected(self):
        env = _valid_env()
        env["retry_limit"] = "-1"
        with pytest.raises(ValidationError, match="retry_limit"):
            OrchestratorSettings(**env)
