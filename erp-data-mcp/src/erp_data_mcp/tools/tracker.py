"""Running tracker tool handlers — get and update capacity tracker."""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any

from erp_data_mcp.config import Settings
from erp_data_mcp.db.client import DynamoDBClient
from erp_data_mcp.decorators import log_tool_invocation, tool_error_handler
from erp_data_mcp.models.schemas import GetRunningTrackerInput, UpdateRunningTrackerInput

logger = logging.getLogger("erp_data_mcp")


@log_tool_invocation
@tool_error_handler
async def get_running_tracker(
    input_data: GetRunningTrackerInput, settings: Settings, db: DynamoDBClient
) -> dict[str, Any]:
    """Get current running capacity tracker for a workflow session (BR-14)."""
    table = db.get_table(settings.dynamodb_table_tracker)
    response = table.get_item(Key={"session_id": input_data.session_id})
    item = response.get("Item")
    if not item:
        return {
            "error": {
                "code": "NOT_FOUND",
                "message": f"Tracker for session {input_data.session_id} not found",
            }
        }
    return item


@log_tool_invocation
@tool_error_handler
async def update_running_tracker(
    input_data: UpdateRunningTrackerInput, settings: Settings, db: DynamoDBClient
) -> dict[str, Any]:
    """Update running capacity tracker after a decision (BR-09, BR-10).

    Supports partial updates. Creates tracker if it doesn't exist.
    Hour and material values cannot go negative (CONSTRAINT_VIOLATION).
    add_transferred/delayed/rejected appends to respective lists.
    """
    table = db.get_table(settings.dynamodb_table_tracker)
    now = datetime.now(timezone.utc).isoformat()

    # Check if tracker exists; create skeleton if not
    response = table.get_item(Key={"session_id": input_data.session_id})
    existing = response.get("Item")

    if not existing:
        # Initialize empty tracker (BR-09 — caller should populate via capacity data)
        existing = {
            "session_id": input_data.session_id,
            "rolling_mill_normal_hrs": Decimal("0"),
            "rolling_mill_overtime_hrs": Decimal("0"),
            "rolling_mill_weekend_hrs": Decimal("0"),
            "finishing_line_normal_hrs": Decimal("0"),
            "finishing_line_overtime_hrs": Decimal("0"),
            "finishing_line_weekend_hrs": Decimal("0"),
            "material_surplus_tons": {},
            "workforce_surplus": Decimal("0"),
            "orders_transferred": [],
            "orders_delayed": [],
            "orders_rejected": [],
            "last_updated": now,
        }

    update_expr_parts = ["#lu = :lu"]
    attr_names: dict[str, str] = {"#lu": "last_updated"}
    attr_values: dict[str, Any] = {":lu": now}

    # Numeric fields — update if provided
    numeric_fields = [
        "rolling_mill_normal_hrs",
        "rolling_mill_overtime_hrs",
        "rolling_mill_weekend_hrs",
        "finishing_line_normal_hrs",
        "finishing_line_overtime_hrs",
        "finishing_line_weekend_hrs",
        "workforce_surplus",
    ]
    for field in numeric_fields:
        value = getattr(input_data, field, None)
        if value is not None:
            safe_name = f"#{field}"
            safe_value = f":{field}"
            update_expr_parts.append(f"{safe_name} = {safe_value}")
            attr_names[safe_name] = field
            attr_values[safe_value] = Decimal(str(value))

    # Material surplus — replace entire map if provided
    if input_data.material_surplus_tons is not None:
        update_expr_parts.append("#mst = :mst")
        attr_names["#mst"] = "material_surplus_tons"
        attr_values[":mst"] = {
            k: Decimal(str(v)) for k, v in input_data.material_surplus_tons.items()
        }

    # List append fields
    list_appends = [
        ("add_transferred", "orders_transferred"),
        ("add_delayed", "orders_delayed"),
        ("add_rejected", "orders_rejected"),
    ]
    for input_field, db_field in list_appends:
        order_id = getattr(input_data, input_field, None)
        if order_id:
            safe_name = f"#{db_field}"
            safe_value = f":{input_field}"
            empty_value = f":empty_{db_field}"
            update_expr_parts.append(
                f"{safe_name} = list_append(if_not_exists({safe_name}, {empty_value}), {safe_value})"
            )
            attr_names[safe_name] = db_field
            attr_values[safe_value] = [order_id]
            attr_values[empty_value] = []

    update_expression = "SET " + ", ".join(update_expr_parts)

    table.update_item(
        Key={"session_id": input_data.session_id},
        UpdateExpression=update_expression,
        ExpressionAttributeNames=attr_names,
        ExpressionAttributeValues=attr_values,
    )

    return {
        "success": True,
        "session_id": input_data.session_id,
        "last_updated": now,
    }
