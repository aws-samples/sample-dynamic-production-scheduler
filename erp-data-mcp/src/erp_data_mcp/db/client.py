"""DynamoDB client singleton with retry configuration."""

from __future__ import annotations

import boto3
from botocore.config import Config


class DynamoDBClient:
    """Singleton DynamoDB resource with adaptive retry and table caching."""

    _instance: DynamoDBClient | None = None

    @classmethod
    def get_instance(cls, region: str = "us-east-1") -> DynamoDBClient:
        """Get or create the singleton DynamoDB client.

        Args:
            region: AWS region name.

        Returns:
            Singleton DynamoDBClient instance.
        """
        if cls._instance is None:
            cls._instance = cls(region)
        return cls._instance

    @classmethod
    def reset(cls) -> None:
        """Reset singleton instance (for testing)."""
        cls._instance = None

    def __init__(self, region: str = "us-east-1") -> None:
        config = Config(
            retries={"mode": "adaptive", "max_attempts": 4},
            connect_timeout=5,
            read_timeout=10,
            region_name=region,
        )
        self._resource = boto3.resource("dynamodb", config=config)
        self._tables: dict[str, object] = {}

    def get_table(self, table_name: str):
        """Get a DynamoDB Table reference, cached after first access.

        Args:
            table_name: DynamoDB table name.

        Returns:
            boto3 DynamoDB Table resource.
        """
        if table_name not in self._tables:
            self._tables[table_name] = self._resource.Table(table_name)
        return self._tables[table_name]
