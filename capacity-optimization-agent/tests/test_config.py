"""Unit tests for AgentSettings configuration."""

import pytest
from pydantic import ValidationError

from capacity_optimization_agent.config import AgentSettings


class TestAgentSettings:
    def test_defaults(self):
        s = AgentSettings()
        assert s.rerouting_window_days == 10
        assert s.delay_threshold_days == 42
        assert s.utilization_warning_pct == 0.90
        assert s.log_level == "INFO"

    def test_custom_values(self, monkeypatch):
        monkeypatch.setenv("REROUTING_WINDOW_DAYS", "15")
        monkeypatch.setenv("DELAY_THRESHOLD_DAYS", "30")
        monkeypatch.setenv("UTILIZATION_WARNING_PCT", "0.85")
        s = AgentSettings()
        assert s.rerouting_window_days == 15
        assert s.delay_threshold_days == 30
        assert s.utilization_warning_pct == 0.85

    def test_zero_window_rejected(self, monkeypatch):
        monkeypatch.setenv("REROUTING_WINDOW_DAYS", "0")
        with pytest.raises(ValidationError):
            AgentSettings()

    def test_utilization_above_one_rejected(self, monkeypatch):
        monkeypatch.setenv("UTILIZATION_WARNING_PCT", "1.5")
        with pytest.raises(ValidationError):
            AgentSettings()

    def test_get_capacity_config(self):
        s = AgentSettings()
        c = s.get_capacity_config()
        assert c.rerouting_window_days == 10
        assert c.delay_threshold_days == 42

    def test_bedrock_model_id_default(self):
        s = AgentSettings()
        assert "claude-haiku-4-5" in s.bedrock_model_id
