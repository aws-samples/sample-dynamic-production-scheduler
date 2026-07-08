"""Shared pytest fixtures — moto-backed DynamoDB for integration tests."""

from __future__ import annotations

import boto3
import pytest
from moto import mock_aws

from erp_data_mcp.config import Settings
from erp_data_mcp.db.client import DynamoDBClient
from erp_data_mcp.seed.data import (
    CUSTOMERS,
    FLORIDA_ORDERS,
    MACHINE_CAPACITY,
    WORKFORCE,
    OHIO_ORDERS,
    RAW_MATERIALS,
)


@pytest.fixture()
def settings() -> Settings:
    """Override Settings with test-prefixed table names."""
    return Settings(
        dynamodb_table_orders="test-orders",
        dynamodb_table_capacity="test-capacity",
        dynamodb_table_workforce="test-workforce",
        dynamodb_table_materials="test-materials",
        dynamodb_table_customers="test-customers",
        dynamodb_table_tracker="test-tracker",
        aws_region="us-east-1",
        log_level="DEBUG",
    )


@pytest.fixture()
def mock_dynamodb(settings: Settings):
    """Create all six DynamoDB tables inside a moto mock."""
    with mock_aws():
        ddb = boto3.resource("dynamodb", region_name=settings.aws_region)

        # orders — PK + GSI
        ddb.create_table(
            TableName=settings.dynamodb_table_orders,
            KeySchema=[{"AttributeName": "order_id", "KeyType": "HASH"}],
            AttributeDefinitions=[
                {"AttributeName": "order_id", "AttributeType": "S"},
                {"AttributeName": "plant", "AttributeType": "S"},
                {"AttributeName": "status", "AttributeType": "S"},
            ],
            GlobalSecondaryIndexes=[
                {
                    "IndexName": "plant-status-index",
                    "KeySchema": [
                        {"AttributeName": "plant", "KeyType": "HASH"},
                        {"AttributeName": "status", "KeyType": "RANGE"},
                    ],
                    "Projection": {"ProjectionType": "ALL"},
                },
            ],
            BillingMode="PAY_PER_REQUEST",
        )

        # capacity — composite key
        ddb.create_table(
            TableName=settings.dynamodb_table_capacity,
            KeySchema=[
                {"AttributeName": "machine_type", "KeyType": "HASH"},
                {"AttributeName": "plant", "KeyType": "RANGE"},
            ],
            AttributeDefinitions=[
                {"AttributeName": "machine_type", "AttributeType": "S"},
                {"AttributeName": "plant", "AttributeType": "S"},
            ],
            BillingMode="PAY_PER_REQUEST",
        )

        # workforce — simple key
        ddb.create_table(
            TableName=settings.dynamodb_table_workforce,
            KeySchema=[{"AttributeName": "plant", "KeyType": "HASH"}],
            AttributeDefinitions=[
                {"AttributeName": "plant", "AttributeType": "S"},
            ],
            BillingMode="PAY_PER_REQUEST",
        )

        # materials — composite key
        ddb.create_table(
            TableName=settings.dynamodb_table_materials,
            KeySchema=[
                {"AttributeName": "material_type", "KeyType": "HASH"},
                {"AttributeName": "plant", "KeyType": "RANGE"},
            ],
            AttributeDefinitions=[
                {"AttributeName": "material_type", "AttributeType": "S"},
                {"AttributeName": "plant", "AttributeType": "S"},
            ],
            BillingMode="PAY_PER_REQUEST",
        )

        # customers — simple key
        ddb.create_table(
            TableName=settings.dynamodb_table_customers,
            KeySchema=[{"AttributeName": "customer_id", "KeyType": "HASH"}],
            AttributeDefinitions=[
                {"AttributeName": "customer_id", "AttributeType": "S"},
            ],
            BillingMode="PAY_PER_REQUEST",
        )

        # tracker — simple key
        ddb.create_table(
            TableName=settings.dynamodb_table_tracker,
            KeySchema=[{"AttributeName": "session_id", "KeyType": "HASH"}],
            AttributeDefinitions=[
                {"AttributeName": "session_id", "AttributeType": "S"},
            ],
            BillingMode="PAY_PER_REQUEST",
        )

        yield ddb


@pytest.fixture()
def db_client(mock_dynamodb) -> DynamoDBClient:
    """Provide a DynamoDBClient wired to the moto mock; reset singleton around test."""
    DynamoDBClient.reset()
    client = DynamoDBClient.get_instance(region="us-east-1")
    yield client
    DynamoDBClient.reset()


@pytest.fixture()
def seed_orders(db_client: DynamoDBClient, settings: Settings) -> None:
    """Load FLORIDA_ORDERS + OHIO_ORDERS into the test orders table."""
    table = db_client.get_table(settings.dynamodb_table_orders)
    with table.batch_writer() as batch:
        for order in FLORIDA_ORDERS + OHIO_ORDERS:
            batch.put_item(Item=order)


@pytest.fixture()
def seed_capacity(db_client: DynamoDBClient, settings: Settings) -> None:
    """Load MACHINE_CAPACITY into the test capacity table."""
    table = db_client.get_table(settings.dynamodb_table_capacity)
    with table.batch_writer() as batch:
        for item in MACHINE_CAPACITY:
            batch.put_item(Item=item)


@pytest.fixture()
def seed_workforce(db_client: DynamoDBClient, settings: Settings) -> None:
    """Load WORKFORCE into the test workforce table."""
    table = db_client.get_table(settings.dynamodb_table_workforce)
    with table.batch_writer() as batch:
        for item in WORKFORCE:
            batch.put_item(Item=item)


@pytest.fixture()
def seed_materials(db_client: DynamoDBClient, settings: Settings) -> None:
    """Load RAW_MATERIALS into the test materials table."""
    table = db_client.get_table(settings.dynamodb_table_materials)
    with table.batch_writer() as batch:
        for item in RAW_MATERIALS:
            batch.put_item(Item=item)


@pytest.fixture()
def seed_customers(db_client: DynamoDBClient, settings: Settings) -> None:
    """Load CUSTOMERS into the test customers table."""
    table = db_client.get_table(settings.dynamodb_table_customers)
    with table.batch_writer() as batch:
        for item in CUSTOMERS:
            batch.put_item(Item=item)
