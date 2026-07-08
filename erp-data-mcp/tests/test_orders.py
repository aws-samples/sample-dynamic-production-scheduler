"""Tests for order tool handlers."""

from __future__ import annotations

import pytest

from erp_data_mcp.models.schemas import (
    GetOrderByIdInput,
    GetOrdersInput,
    UpdateOrderPriorityInput,
    UpdateOrderStatusInput,
)
from erp_data_mcp.tools.orders import (
    get_order_by_id,
    get_orders,
    update_order_priority,
    update_order_status,
)


@pytest.mark.asyncio
class TestGetOrders:
    async def test_get_florida_orders(self, settings, db_client, seed_orders):
        result = await get_orders(
            GetOrdersInput(plant="Florida"), settings, db_client,
        )
        assert result["count"] == 20

    async def test_get_ohio_orders(self, settings, db_client, seed_orders):
        result = await get_orders(
            GetOrdersInput(plant="Ohio"), settings, db_client,
        )
        assert result["count"] == 20

    async def test_get_orders_with_status_filter(self, settings, db_client, seed_orders):
        result = await get_orders(
            GetOrdersInput(plant="Florida", status="Active"), settings, db_client,
        )
        assert all(o["status"] == "Active" for o in result["orders"])

    async def test_get_orders_empty_result(self, settings, db_client, seed_orders):
        result = await get_orders(
            GetOrdersInput(plant="Florida", status="Cancelled"), settings, db_client,
        )
        assert result["count"] == 0


@pytest.mark.asyncio
class TestGetOrderById:
    async def test_found(self, settings, db_client, seed_orders):
        result = await get_order_by_id(
            GetOrderByIdInput(order_id="PO-2026-001"), settings, db_client,
        )
        assert result["order"]["order_id"] == "PO-2026-001"

    async def test_not_found(self, settings, db_client, seed_orders):
        result = await get_order_by_id(
            GetOrderByIdInput(order_id="PO-2026-999"), settings, db_client,
        )
        assert result["error"]["code"] == "NOT_FOUND"


@pytest.mark.asyncio
class TestUpdateOrderPriority:
    async def test_valid_update(self, settings, db_client, seed_orders):
        result = await update_order_priority(
            UpdateOrderPriorityInput(order_id="PO-2026-001", priority="P1"),
            settings,
            db_client,
        )
        assert result["success"] is True

    async def test_not_found(self, settings, db_client, seed_orders):
        result = await update_order_priority(
            UpdateOrderPriorityInput(order_id="PO-2026-999", priority="P1"),
            settings,
            db_client,
        )
        assert result["error"]["code"] == "NOT_FOUND"

    async def test_ohio_order_rejected(self, settings, db_client, seed_orders):
        result = await update_order_priority(
            UpdateOrderPriorityInput(order_id="PO-2026-021", priority="P1"),
            settings,
            db_client,
        )
        assert result["error"]["code"] == "INVALID_INPUT"
        assert "Florida" in result["error"]["message"]


@pytest.mark.asyncio
class TestUpdateOrderStatus:
    async def test_active_to_transferred(self, settings, db_client, seed_orders):
        result = await update_order_status(
            UpdateOrderStatusInput(order_id="PO-2026-001", status="Transferred"),
            settings,
            db_client,
        )
        assert result["success"] is True

    async def test_active_to_delayed(self, settings, db_client, seed_orders):
        result = await update_order_status(
            UpdateOrderStatusInput(order_id="PO-2026-002", status="Delayed"),
            settings,
            db_client,
        )
        assert result["success"] is True

    async def test_terminal_state_rejected(self, settings, db_client, seed_orders):
        # First transition to terminal state
        await update_order_status(
            UpdateOrderStatusInput(order_id="PO-2026-003", status="Transferred"),
            settings,
            db_client,
        )
        # Attempt another transition from terminal state
        result = await update_order_status(
            UpdateOrderStatusInput(order_id="PO-2026-003", status="Active"),
            settings,
            db_client,
        )
        assert result["error"]["code"] == "INVALID_TRANSITION"

    async def test_not_found(self, settings, db_client, seed_orders):
        result = await update_order_status(
            UpdateOrderStatusInput(order_id="PO-2026-999", status="Delayed"),
            settings,
            db_client,
        )
        assert result["error"]["code"] == "NOT_FOUND"
