"""Unit tests for agent configuration."""

import pytest
from pydantic import ValidationError

from impact_assessment_agent.config import AgentSettings


class TestAgentSettings:
    def test_default_settings_valid(self):
        s = AgentSettings()
        assert s.weight_urgency == 0.40
        assert s.p1_threshold == 75
        assert s.bedrock_model_id.startswith("us.anthropic")

    def test_get_scoring_weights(self):
        s = AgentSettings()
        w = s.get_scoring_weights()
        assert w.urgency == 0.40
        assert w.customer_tier == 0.25

    def test_get_priority_thresholds(self):
        s = AgentSettings()
        t = s.get_priority_thresholds()
        assert t.p1 == 75
        assert t.p2 == 50

    def test_invalid_weights_rejected(self):
        with pytest.raises(ValidationError):
            AgentSettings(
                weight_urgency=0.90,
                weight_customer_tier=0.90,
                weight_order_value=0.10,
                weight_machine_complexity=0.10,
            )

    def test_invalid_thresholds_rejected(self):
        with pytest.raises(ValidationError):
            AgentSettings(p1_threshold=30, p2_threshold=60)

    def test_custom_valid_settings(self):
        s = AgentSettings(
            weight_urgency=0.50,
            weight_customer_tier=0.20,
            weight_order_value=0.20,
            weight_machine_complexity=0.10,
            p1_threshold=80,
            p2_threshold=40,
        )
        assert s.weight_urgency == 0.50
        assert s.p1_threshold == 80
