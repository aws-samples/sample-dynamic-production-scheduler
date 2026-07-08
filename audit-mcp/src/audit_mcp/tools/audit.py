"""Audit trail tool handlers — write_audit_entry and get_audit_trail."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from boto3.dynamodb.conditions import Key

from audit_mcp.config import Settings
from audit_mcp.db.client import DynamoDBClient
from audit_mcp.decorators import log_tool_invocation, tool_error_handler
from audit_mcp.models.schemas import GetAuditTrailInput, WriteAuditEntryInput


@tool_error_handler
@log_tool_invocation
async def write_audit_entry(
    params: WriteAuditEntryInput,
    settings: Settings,
    db: DynamoDBClient,
) -> dict:
    """Write a single audit entry to DynamoDB.

    Generates entry_id (UUID v4) and created_at server-side.
    Returns {"entry_id": "<uuid>", "status": "created"}.
    """
    table = db.get_table(settings.dynamodb_table_audit)
    entry_id = str(uuid.uuid4())
    created_at = datetime.now(timezone.utc).isoformat()

    item = {
        "session_id": params.session_id,
        "entry_id": entry_id,
        "agent": params.agent,
        "action": params.action,
        "details": params.details,
        "timestamp": params.timestamp,
        "created_at": created_at,
    }

    table.put_item(Item=item)
    return {"entry_id": entry_id, "status": "created"}


@tool_error_handler
@log_tool_invocation
async def get_audit_trail(
    params: GetAuditTrailInput,
    settings: Settings,
    db: DynamoDBClient,
) -> dict:
    """Query audit entries for a session.

    Supports optional filtering by agent (via GSI) and start_time.
    Returns {"entries": [...], "count": <n>}.
    """
    table = db.get_table(settings.dynamodb_table_audit)

    if params.agent:
        # Use GSI for agent-filtered queries
        response = table.query(
            IndexName="session-agent-index",
            KeyConditionExpression=(
                Key("session_id").eq(params.session_id)
                & Key("agent").eq(params.agent)
            ),
        )
    else:
        response = table.query(
            KeyConditionExpression=Key("session_id").eq(params.session_id),
        )

    entries = response.get("Items", [])

    # Apply start_time filter if provided
    if params.start_time:
        entries = [e for e in entries if e.get("timestamp", "") >= params.start_time]

    # Sort by timestamp ascending
    entries.sort(key=lambda e: e.get("timestamp", ""))

    return {"entries": entries, "count": len(entries)}
