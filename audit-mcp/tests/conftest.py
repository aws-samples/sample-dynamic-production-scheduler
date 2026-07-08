"""Shared pytest fixtures — moto-backed DynamoDB for audit tests."""

from __future__ import annotations

import boto3
import pytest
from moto import mock_aws

from audit_mcp.config import Settings
from audit_mcp.db.client import DynamoDBClient


@pytest.fixture()
def settings() -> Settings:
    """Override Settings with test-prefixed table name."""
    return Settings(
        dynamodb_table_audit="test-audit",
        aws_region="us-east-1",
        log_level="DEBUG",
    )


@pytest.fixture()
def mock_dynamodb(settings: Settings):
    """Create audit DynamoDB table inside a moto mock."""
    with mock_aws():
        ddb = boto3.resource("dynamodb", region_name=settings.aws_region)

        ddb.create_table(
            TableName=settings.dynamodb_table_audit,
            KeySchema=[
                {"AttributeName": "session_id", "KeyType": "HASH"},
                {"AttributeName": "entry_id", "KeyType": "RANGE"},
            ],
            AttributeDefinitions=[
                {"AttributeName": "session_id", "AttributeType": "S"},
                {"AttributeName": "entry_id", "AttributeType": "S"},
                {"AttributeName": "agent", "AttributeType": "S"},
            ],
            GlobalSecondaryIndexes=[
                {
                    "IndexName": "session-agent-index",
                    "KeySchema": [
                        {"AttributeName": "session_id", "KeyType": "HASH"},
                        {"AttributeName": "agent", "KeyType": "RANGE"},
                    ],
                    "Projection": {"ProjectionType": "ALL"},
                },
            ],
            BillingMode="PAY_PER_REQUEST",
        )

        yield ddb


@pytest.fixture()
def db_client(mock_dynamodb) -> DynamoDBClient:
    """Provide a DynamoDBClient wired to the moto mock."""
    DynamoDBClient.reset()
    client = DynamoDBClient.get_instance(region="us-east-1")
    yield client
    DynamoDBClient.reset()
