"""Tests for capacity tool handlers."""

import pytest

from erp_data_mcp.config import Settings
from erp_data_mcp.db.client import DynamoDBClient
from erp_data_mcp.models.schemas import GetMachineCapacityInput, GetMaterialsInput
from erp_data_mcp.tools.capacity import get_machine_capacity, get_workforce, get_materials


@pytest.mark.asyncio
class TestGetMachineCapacity:
    async def test_rolling_mill(self, settings, db_client, seed_capacity):
        inp = GetMachineCapacityInput(machine_type="Rolling Mill")
        result = await get_machine_capacity(inp, settings, db_client)
        assert result["machine_type"] == "Rolling Mill"
        assert "Steel Sheets" in result["product_families_supported"]

    async def test_finishing_line(self, settings, db_client, seed_capacity):
        inp = GetMachineCapacityInput(machine_type="Finishing Line")
        result = await get_machine_capacity(inp, settings, db_client)
        assert result["machine_type"] == "Finishing Line"

    async def test_not_found_invalid_type(self, settings, db_client):
        inp = GetMachineCapacityInput(machine_type="Rolling Mill")
        result = await get_machine_capacity(inp, settings, db_client)
        assert result["error"]["code"] == "NOT_FOUND"


@pytest.mark.asyncio
class TestGetWorkforce:
    async def test_returns_ohio_data(self, settings, db_client, seed_workforce):
        result = await get_workforce(settings, db_client)
        assert result["plant"] == "Ohio"
        assert "total_operators" in result

    async def test_not_found_no_data(self, settings, db_client):
        result = await get_workforce(settings, db_client)
        assert result["error"]["code"] == "NOT_FOUND"


@pytest.mark.asyncio
class TestGetMaterials:
    async def test_all_materials(self, settings, db_client, seed_materials):
        result = await get_materials(None, settings, db_client)
        assert len(result["materials"]) == 3

    async def test_filter_by_type(self, settings, db_client, seed_materials):
        inp = GetMaterialsInput(material_type="Hot-Rolled Coil")
        result = await get_materials(inp, settings, db_client)
        assert len(result["materials"]) == 1

    async def test_not_found(self, settings, db_client):
        inp = GetMaterialsInput(material_type="Steel Slab")
        result = await get_materials(inp, settings, db_client)
        assert result["error"]["code"] == "NOT_FOUND"
