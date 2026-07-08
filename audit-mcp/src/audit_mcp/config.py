"""Environment-based configuration using Pydantic Settings."""

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    aws_region: str = "us-east-1"
    dynamodb_table_audit: str = "disruptionai-audit"
    log_level: str = "INFO"

    model_config = {"env_prefix": ""}
