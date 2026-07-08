"""Agent configuration — loaded from environment variables at startup.

Validates business thresholds at startup. Fails fast on invalid
configuration (Pattern 5: env-based config).
"""

from __future__ import annotations

from pydantic import model_validator
from pydantic_settings import BaseSettings

from capacity_optimization_agent.models.schemas import CapacityAgentConfig


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

    # Business thresholds
    rerouting_window_days: int = 10
    delay_threshold_days: int = 42
    utilization_warning_pct: float = 0.90

    # AgentCore Memory
    agentcore_memory_id: str = ""

    # Logging
    log_level: str = "INFO"

    model_config = {"env_prefix": ""}

    @model_validator(mode="after")
    def validate_config(self) -> "AgentSettings":
        """Validate business thresholds at startup."""
        CapacityAgentConfig(
            rerouting_window_days=self.rerouting_window_days,
            delay_threshold_days=self.delay_threshold_days,
            utilization_warning_pct=self.utilization_warning_pct,
        )
        return self

    def get_capacity_config(self) -> CapacityAgentConfig:
        """Return validated CapacityAgentConfig instance."""
        return CapacityAgentConfig(
            rerouting_window_days=self.rerouting_window_days,
            delay_threshold_days=self.delay_threshold_days,
            utilization_warning_pct=self.utilization_warning_pct,
        )
