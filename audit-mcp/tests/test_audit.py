"""Tests for audit tool handlers — write_audit_entry and get_audit_trail."""

from __future__ import annotations

from datetime import datetime, timezone

import pytest

from audit_mcp.config import Settings
from audit_mcp.db.client import DynamoDBClient
from audit_mcp.models.schemas import (
    GetAuditTrailInput,
    WriteAuditEntryInput,
)
from audit_mcp.tools.audit import get_audit_trail, write_audit_entry


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


@pytest.mark.asyncio
async def test_write_audit_entry_creates_entry(
    db_client: DynamoDBClient, settings: Settings
):
    params = WriteAuditEntryInput(
        session_id="sess-001",
        agent="orchestrator",
        action="start_workflow",
        details={"event": "tornado"},
        timestamp=_now_iso(),
    )
    result = await write_audit_entry(params, settings, db_client)
    assert result["status"] == "created"
    assert "entry_id" in result
    assert len(result["entry_id"]) == 36  # UUID format


@pytest.mark.asyncio
async def test_write_multiple_entries_unique_ids(
    db_client: DynamoDBClient, settings: Settings
):
    ids = set()
    for i in range(3):
        params = WriteAuditEntryInput(
            session_id="sess-001",
            agent="planner",
            action=f"action_{i}",
            details={"step": i},
            timestamp=_now_iso(),
        )
        result = await write_audit_entry(params, settings, db_client)
        ids.add(result["entry_id"])
    assert len(ids) == 3


@pytest.mark.asyncio
async def test_get_audit_trail_empty_session(
    db_client: DynamoDBClient, settings: Settings
):
    params = GetAuditTrailInput(session_id="nonexistent")
    result = await get_audit_trail(params, settings, db_client)
    assert result["entries"] == []
    assert result["count"] == 0


@pytest.mark.asyncio
async def test_get_audit_trail_returns_written_entries(
    db_client: DynamoDBClient, settings: Settings
):
    # Write 2 entries
    for action in ["action_a", "action_b"]:
        params = WriteAuditEntryInput(
            session_id="sess-002",
            agent="capacity_agent",
            action=action,
            details={"info": action},
            timestamp=_now_iso(),
        )
        await write_audit_entry(params, settings, db_client)

    # Read back
    result = await get_audit_trail(
        GetAuditTrailInput(session_id="sess-002"), settings, db_client
    )
    assert result["count"] == 2
    actions = [e["action"] for e in result["entries"]]
    assert "action_a" in actions
    assert "action_b" in actions


@pytest.mark.asyncio
async def test_get_audit_trail_filter_by_agent(
    db_client: DynamoDBClient, settings: Settings
):
    # Write entries from different agents
    for agent in ["orchestrator", "planner", "orchestrator"]:
        params = WriteAuditEntryInput(
            session_id="sess-003",
            agent=agent,
            action="test",
            details={"a": 1},
            timestamp=_now_iso(),
        )
        await write_audit_entry(params, settings, db_client)

    # Filter by orchestrator
    result = await get_audit_trail(
        GetAuditTrailInput(session_id="sess-003", agent="orchestrator"),
        settings,
        db_client,
    )
    assert result["count"] == 2
    assert all(e["agent"] == "orchestrator" for e in result["entries"])


@pytest.mark.asyncio
async def test_get_audit_trail_filter_by_start_time(
    db_client: DynamoDBClient, settings: Settings
):
    ts_early = "2026-03-16T10:00:00+00:00"
    ts_late = "2026-03-16T14:00:00+00:00"

    for ts in [ts_early, ts_late]:
        params = WriteAuditEntryInput(
            session_id="sess-004",
            agent="scheduler_agent",
            action="schedule",
            details={"t": ts},
            timestamp=ts,
        )
        await write_audit_entry(params, settings, db_client)

    # Filter: only entries >= 12:00
    result = await get_audit_trail(
        GetAuditTrailInput(
            session_id="sess-004",
            start_time="2026-03-16T12:00:00+00:00",
        ),
        settings,
        db_client,
    )
    assert result["count"] == 1
    assert result["entries"][0]["timestamp"] == ts_late


@pytest.mark.asyncio
async def test_get_audit_trail_sorted_by_timestamp(
    db_client: DynamoDBClient, settings: Settings
):
    timestamps = [
        "2026-03-16T15:00:00+00:00",
        "2026-03-16T10:00:00+00:00",
        "2026-03-16T12:00:00+00:00",
    ]
    for ts in timestamps:
        params = WriteAuditEntryInput(
            session_id="sess-005",
            agent="production_order_agent",
            action="prioritize",
            details={"ts": ts},
            timestamp=ts,
        )
        await write_audit_entry(params, settings, db_client)

    result = await get_audit_trail(
        GetAuditTrailInput(session_id="sess-005"), settings, db_client
    )
    ts_list = [e["timestamp"] for e in result["entries"]]
    assert ts_list == sorted(ts_list)


@pytest.mark.asyncio
async def test_entries_isolated_by_session(
    db_client: DynamoDBClient, settings: Settings
):
    # Write to two different sessions
    for sid in ["sess-A", "sess-B"]:
        params = WriteAuditEntryInput(
            session_id=sid,
            agent="planner",
            action="decide",
            details={"sid": sid},
            timestamp=_now_iso(),
        )
        await write_audit_entry(params, settings, db_client)

    result_a = await get_audit_trail(
        GetAuditTrailInput(session_id="sess-A"), settings, db_client
    )
    result_b = await get_audit_trail(
        GetAuditTrailInput(session_id="sess-B"), settings, db_client
    )
    assert result_a["count"] == 1
    assert result_b["count"] == 1
    assert result_a["entries"][0]["details"]["sid"] == "sess-A"
