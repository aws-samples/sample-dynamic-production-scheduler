"""Unit tests for Constraint Matching Agent configuration."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from constraint_matching_agent.config import AgentSettings


class TestAgentSettings:
    def test_defaults(self):
        s = AgentSettings()
        assert s.utilization_warning_pct == 0.90
        assert s.max_cascade_depth == 5
        assert s.cascade_timeout_secs == 3
        assert s.checkpoint_interval_secs == 300
        assert s.log_level == "INFO"

    def test_custom_values(self, monkeypatch):
        monkeypatch.setenv("UTILIZATION_WARNING_PCT", "0.85")
        monkeypatch.setenv("MAX_CASCADE_DEPTH", "3")
        monkeypatch.setenv("CASCADE_TIMEOUT_SECS", "5")
        s = AgentSettings()
        assert s.utilization_warning_pct == 0.85
        assert s.max_cascade_depth == 3
        assert s.cascade_timeout_secs == 5

    def test_invalid_warning_pct(self, monkeypatch):
        monkeypatch.setenv("UTILIZATION_WARNING_PCT", "1.5")
        with pytest.raises(ValidationError):
            AgentSettings()

    def test_invalid_cascade_depth(self, monkeypatch):
        monkeypatch.setenv("MAX_CASCADE_DEPTH", "0")
        with pytest.raises(ValidationError):
            AgentSettings()

    def test_get_agent_config(self):
        s = AgentSettings()
        cfg = s.get_agent_config()
        assert cfg.utilization_warning_pct == 0.90
        assert cfg.max_cascade_depth == 5

    def test_model_id_default(self):
        s = AgentSettings()
        assert "claude" in s.bedrock_model_id
