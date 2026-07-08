"""Tests for tracker tool handlers."""

import pytest

from erp_data_mcp.config import Settings
from erp_data_mcp.db.client import DynamoDBClient
from erp_data_mcp.models.schemas import GetRunningTrackerInput, UpdateRunningTrackerInput
from erp_data_mcp.tools.tracker import get_running_tracker, update_running_tracker

TEST_SESSION_ID = "550e8400-e29b-41d4-a716-446655440000"


@pytest.mark.asyncio
class TestGetRunningTracker:
    async def test_not_found(self, settings, db_client):
        inp = GetRunningTrackerInput(session_id=TEST_SESSION_ID)
        result = await get_running_tracker(inp, settings, db_client)
        assert result["error"]["code"] == "NOT_FOUND"


@pytest.mark.asyncio
class TestUpdateRunningTracker:
    async def test_create_new_tracker(self, settings, db_client):
        inp = UpdateRunningTrackerInput(
            session_id=TEST_SESSION_ID,
            rolling_mill_normal_hrs=10.0,
        )
        result = await update_running_tracker(inp, settings, db_client)
        assert result["success"] is True

    async def test_partial_update(self, settings, db_client):
        # Create tracker first
        create_inp = UpdateRunningTrackerInput(
            session_id=TEST_SESSION_ID,
            rolling_mill_normal_hrs=10.0,
        )
        await update_running_tracker(create_inp, settings, db_client)

        # Partial update
        update_inp = UpdateRunningTrackerInput(
            session_id=TEST_SESSION_ID,
            finishing_line_normal_hrs=5.0,
        )
        result = await update_running_tracker(update_inp, settings, db_client)
        assert result["success"] is True

    async def test_add_transferred_order(self, settings, db_client):
        update_inp = UpdateRunningTrackerInput(
            session_id=TEST_SESSION_ID,
            add_transferred="PO-2026-001",
        )
        await update_running_tracker(update_inp, settings, db_client)

        get_inp = GetRunningTrackerInput(session_id=TEST_SESSION_ID)
        result = await get_running_tracker(get_inp, settings, db_client)
        assert "PO-2026-001" in result["orders_transferred"]

    async def test_add_multiple_list_items(self, settings, db_client):
        # Add transferred order
        transferred_inp = UpdateRunningTrackerInput(
            session_id=TEST_SESSION_ID,
            add_transferred="PO-2026-001",
        )
        await update_running_tracker(transferred_inp, settings, db_client)

        # Add delayed order
        delayed_inp = UpdateRunningTrackerInput(
            session_id=TEST_SESSION_ID,
            add_delayed="PO-2026-002",
        )
        await update_running_tracker(delayed_inp, settings, db_client)

        # Verify both lists populated
        get_inp = GetRunningTrackerInput(session_id=TEST_SESSION_ID)
        result = await get_running_tracker(get_inp, settings, db_client)
        assert len(result["orders_transferred"]) > 0
        assert len(result["orders_delayed"]) > 0
