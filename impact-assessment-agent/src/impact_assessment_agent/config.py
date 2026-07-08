"""Agent configuration — loaded from environment variables at startup.

Validates scoring weights sum to 1.0 and P1 > P2 thresholds.
Fails fast on invalid configuration (Pattern 5).
"""

from __future__ import annotations

from pydantic import model_validator
from pydantic_settings import BaseSettings

from impact_assessment_agent.models.schemas import (
    PriorityThresholds,
    ScoringWeights,
)


class AgentSettings(BaseSettings):
    """All configurable agent parameters. Loaded from env vars."""

    # LLM
    bedrock_model_id: str = (
        "us.anthropic.claude-haiku-4-5-20251001-v1:0"
    )

    # AgentCore Gateway endpoint
    gateway_url: str = ""

    # Cognito OAuth2 configuration
    cognito_token_endpoint: str = ""
    cognito_client_id: str = ""
    cognito_client_secret: str = ""
    erp_data_scope: str = "disruptionai-gateway/erp-data"

    # Scoring weights
    weight_urgency: float = 0.40
    weight_customer_tier: float = 0.25
    weight_order_value: float = 0.20
    weight_machine_complexity: float = 0.15

    # Priority thresholds
    p1_threshold: int = 75
    p2_threshold: int = 50

    # AgentCore Memory
    agentcore_memory_id: str = ""

    # Logging
    log_level: str = "INFO"

    model_config = {"env_prefix": ""}

    @model_validator(mode="after")
    def validate_config(self) -> "AgentSettings":
        """Validate weights and thresholds at startup."""
        # This will raise if weights don't sum to 1.0
        ScoringWeights(
            urgency=self.weight_urgency,
            customer_tier=self.weight_customer_tier,
            order_value=self.weight_order_value,
            machine_complexity=self.weight_machine_complexity,
        )
        # This will raise if p1 <= p2
        PriorityThresholds(
            p1=self.p1_threshold,
            p2=self.p2_threshold,
        )
        return self

    def get_scoring_weights(self) -> ScoringWeights:
        """Return validated ScoringWeights instance."""
        return ScoringWeights(
            urgency=self.weight_urgency,
            customer_tier=self.weight_customer_tier,
            order_value=self.weight_order_value,
            machine_complexity=self.weight_machine_complexity,
        )

    def get_priority_thresholds(self) -> PriorityThresholds:
        """Return validated PriorityThresholds instance."""
        return PriorityThresholds(
            p1=self.p1_threshold,
            p2=self.p2_threshold,
        )
