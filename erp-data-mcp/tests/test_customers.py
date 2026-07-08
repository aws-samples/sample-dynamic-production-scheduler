"""Tests for customer tool handler."""

import pytest

from erp_data_mcp.config import Settings
from erp_data_mcp.db.client import DynamoDBClient
from erp_data_mcp.models.schemas import GetCustomersInput
from erp_data_mcp.tools.customers import get_customers


@pytest.mark.asyncio
class TestGetCustomers:
    async def test_all_customers(self, settings, db_client, seed_customers):
        result = await get_customers(None, settings, db_client)
        assert len(result["customers"]) == 10

    async def test_filter_by_id(self, settings, db_client, seed_customers):
        inp = GetCustomersInput(customer_id="CUST-1001")
        result = await get_customers(inp, settings, db_client)
        assert len(result["customers"]) == 1
        assert result["customers"][0]["customer_name"] == "Acme Manufacturing"

    async def test_not_found(self, settings, db_client, seed_customers):
        inp = GetCustomersInput(customer_id="CUST-9999")
        result = await get_customers(inp, settings, db_client)
        assert result["error"]["code"] == "NOT_FOUND"
