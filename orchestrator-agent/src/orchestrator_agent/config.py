"""Agent configuration — loaded from environment variables at startup.

Validates sub-agent IDs, timeouts, and retry limits.
Fails fast on invalid configuration (Pattern 5, SECURITY-12).
"""

from __future__ import annotations

from pydantic import model_validator
from pydantic_settings import BaseSettings


class OrchestratorSettings(BaseSettings):
    """All configurable Orchestrator Agent parameters."""

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
    audit_scope: str = "disruptionai-gateway/audit"

    # Sub-agent ARNs (AgentCore managed runtime — set via environment variables)
    impact_assessment_agent_arn: str = ""
    capacity_optimization_agent_arn: str = ""
    constraint_matching_agent_arn: str = ""

    # Session
    session_timeout_minutes: int = 60
    max_turns: int = 100
    retry_limit: int = 1
    retry_delay_seconds: int = 30

    # AgentCore Memory
    agentcore_memory_id: str = ""

    # Logging
    log_level: str = "INFO"

    model_config = {"env_prefix": ""}

    @model_validator(mode="after")
    def validate_config(self) -> "OrchestratorSettings":
        """Validate required fields at startup."""
        for name in (
            "impact_assessment_agent_arn",
            "capacity_optimization_agent_arn",
            "constraint_matching_agent_arn",
        ):
            if not getattr(self, name):
                raise ValueError(f"{name} must be non-empty")
        if self.session_timeout_minutes <= 0:
            raise ValueError("session_timeout_minutes must be > 0")
        if self.retry_limit < 0:
            raise ValueError("retry_limit must be >= 0")
        return self
