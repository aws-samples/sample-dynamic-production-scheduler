"""Environment-based configuration using Pydantic Settings."""

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    aws_region: str = "us-east-1"
    dynamodb_table_orders: str = "disruptionai-orders"
    dynamodb_table_capacity: str = "disruptionai-capacity"
    dynamodb_table_workforce: str = "disruptionai-manpower"
    dynamodb_table_materials: str = "disruptionai-materials"
    dynamodb_table_customers: str = "disruptionai-customers"
    dynamodb_table_tracker: str = "disruptionai-tracker"
    log_level: str = "INFO"

    model_config = {"env_prefix": ""}
