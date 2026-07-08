"""Order tool handlers — get, query, update priority and status."""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any

from boto3.dynamodb.conditions import Attr, Key

from erp_data_mcp.config import Settings
from erp_data_mcp.db.client import DynamoDBClient
from erp_data_mcp.decorators import log_tool_invocation, tool_error_handler
from erp_data_mcp.models.schemas import (
    GetOrderByIdInput,
    GetOrdersInput,
    UpdateOrderPriorityInput,
    UpdateOrderStatusInput,
)

logger = logging.getLogger("erp_data_mcp")

# Valid status transitions (BR-05)
VALID_TRANSITIONS: dict[str, set[str]] = {
    "Active": {"Delayed", "Transferred", "Cancelled"},
    "Delayed": {"Active"},
    # Transferred and Cancelled are terminal — no transitions allowed
}


@log_tool_invocation
@tool_error_handler
async def get_orders(input_data: GetOrdersInput, settings: Settings, db: DynamoDBClient) -> dict[str, Any]:
    """Query production orders by plant with optional status filter (BR-02, BR-18).

    Uses GSI plant-status-index for efficient querying.
    """
    table = db.get_table(settings.dynamodb_table_orders)

    key_condition = Key("plant").eq(input_data.plant)
    if input_data.status:
        key_condition = key_condition & Key("status").eq(input_data.status)

    response = table.query(
        IndexName="plant-status-index",
        KeyConditionExpression=key_condition,
    )
    items = response.get("Items", [])
    return {"orders": items, "count": len(items)}


@log_tool_invocation
@tool_error_handler
async def get_order_by_id(input_data: GetOrderByIdInput, settings: Settings, db: DynamoDBClient) -> dict[str, Any]:
    """Retrieve a single order by ID (BR-01)."""
    table = db.get_table(settings.dynamodb_table_orders)
    response = table.get_item(Key={"order_id": input_data.order_id})
    item = response.get("Item")
    if not item:
        return {"error": {"code": "NOT_FOUND", "message": f"Order {input_data.order_id} not found"}}
    return {"order": item}


@log_tool_invocation
@tool_error_handler
async def update_order_priority(
    input_data: UpdateOrderPriorityInput, settings: Settings, db: DynamoDBClient
) -> dict[str, Any]:
    """Update priority classification for an order (BR-04).

    Only Florida orders can have priority updated.
    """
    table = db.get_table(settings.dynamodb_table_orders)

    # Verify order exists and is from Florida
    response = table.get_item(Key={"order_id": input_data.order_id})
    item = response.get("Item")
    if not item:
        return {"error": {"code": "NOT_FOUND", "message": f"Order {input_data.order_id} not found"}}
    if item.get("plant") != "Florida":
        return {
            "error": {
                "code": "INVALID_INPUT",
                "message": "Only Florida orders can have priority updated",
            }
        }

    now = datetime.now(timezone.utc).isoformat()
    table.update_item(
        Key={"order_id": input_data.order_id},
        UpdateExpression="SET priority = :p, updated_at = :u",
        ExpressionAttributeValues={":p": input_data.priority, ":u": now},
    )
    return {
        "success": True,
        "order": {
            "order_id": input_data.order_id,
            "priority": input_data.priority,
            "updated_at": now,
        },
    }


@log_tool_invocation
@tool_error_handler
async def update_order_status(
    input_data: UpdateOrderStatusInput, settings: Settings, db: DynamoDBClient
) -> dict[str, Any]:
    """Update order status with transition validation (BR-05, BR-16).

    Uses DynamoDB conditional writes to prevent stale updates.
    Valid transitions: Active->Delayed/Transferred/Cancelled, Delayed->Active.
    Transferred and Cancelled are terminal states.
    """
    table = db.get_table(settings.dynamodb_table_orders)

    # Get current order
    response = table.get_item(Key={"order_id": input_data.order_id})
    item = response.get("Item")
    if not item:
        return {"error": {"code": "NOT_FOUND", "message": f"Order {input_data.order_id} not found"}}

    current_status = item.get("status")
    allowed = VALID_TRANSITIONS.get(current_status, set())
    if input_data.status not in allowed:
        return {
            "error": {
                "code": "INVALID_TRANSITION",
                "message": f"Cannot transition from {current_status} to {input_data.status}",
            }
        }

    now = datetime.now(timezone.utc).isoformat()
    # Conditional write to ensure status hasn't changed since we read it (BR-16)
    table.update_item(
        Key={"order_id": input_data.order_id},
        UpdateExpression="SET #s = :new_status, updated_at = :u",
        ConditionExpression=Attr("status").eq(current_status),
        ExpressionAttributeNames={"#s": "status"},
        ExpressionAttributeValues={":new_status": input_data.status, ":u": now},
    )
    return {
        "success": True,
        "order": {
            "order_id": input_data.order_id,
            "status": input_data.status,
            "updated_at": now,
        },
    }
