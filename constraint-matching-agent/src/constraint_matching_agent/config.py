"""Agent configuration — loaded from environment variables at startup.

Validates business thresholds at startup. Fails fast on invalid
configuration (Pattern 5: env-based config).
"""

from __future__ import annotations

from pydantic import model_validator
from pydantic_settings import BaseSettings

from constraint_matching_agent.models.schemas import AgentConfig


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
    utilization_warning_pct: float = 0.90
    max_cascade_depth: int = 5
    cascade_timeout_secs: int = 3
    checkpoint_interval_secs: int = 300

    # AgentCore Memory
    agentcore_memory_id: str = ""

    # Logging
    log_level: str = "INFO"

    model_config = {"env_prefix": ""}

    @model_validator(mode="after")
    def validate_config(self) -> "AgentSettings":
        """Validate business thresholds at startup."""
        AgentConfig(
            utilization_warning_pct=self.utilization_warning_pct,
            max_cascade_depth=self.max_cascade_depth,
            cascade_timeout_secs=self.cascade_timeout_secs,
            checkpoint_interval_secs=self.checkpoint_interval_secs,
        )
        return self

    def get_agent_config(self) -> AgentConfig:
        """Return validated AgentConfig instance."""
        return AgentConfig(
            utilization_warning_pct=self.utilization_warning_pct,
            max_cascade_depth=self.max_cascade_depth,
            cascade_timeout_secs=self.cascade_timeout_secs,
            checkpoint_interval_secs=self.checkpoint_interval_secs,
        )
