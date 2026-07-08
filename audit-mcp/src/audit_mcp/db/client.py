"""DynamoDB client singleton with adaptive retry."""

from __future__ import annotations

import logging

import boto3
from botocore.config import Config

logger = logging.getLogger("audit_mcp")

_RETRY_CONFIG = Config(
    retries={"max_attempts": 3, "mode": "adaptive"},
)


class DynamoDBClient:
    """Singleton wrapper around boto3 DynamoDB resource."""

    _instance: DynamoDBClient | None = None

    def __init__(self, region: str) -> None:
        self._resource = boto3.resource(
            "dynamodb",
            region_name=region,
            config=_RETRY_CONFIG,
        )

    @classmethod
    def get_instance(cls, region: str = "us-east-1") -> DynamoDBClient:
        if cls._instance is None:
            cls._instance = cls(region)
        return cls._instance

    @classmethod
    def reset(cls) -> None:
        """Reset singleton — used in tests."""
        cls._instance = None

    def get_table(self, table_name: str):
        """Return a DynamoDB Table resource."""
        return self._resource.Table(table_name)
