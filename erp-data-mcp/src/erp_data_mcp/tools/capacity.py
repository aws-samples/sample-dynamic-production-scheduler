"""Capacity tool handlers — machine capacity, workforce, materials."""

from __future__ import annotations

import logging
from typing import Any, Optional

from boto3.dynamodb.conditions import Key

from erp_data_mcp.config import Settings
from erp_data_mcp.db.client import DynamoDBClient
from erp_data_mcp.decorators import log_tool_invocation, tool_error_handler
from erp_data_mcp.models.schemas import GetMachineCapacityInput, GetMaterialsInput

logger = logging.getLogger("erp_data_mcp")


@log_tool_invocation
@tool_error_handler
async def get_machine_capacity(
    input_data: GetMachineCapacityInput, settings: Settings, db: DynamoDBClient
) -> dict[str, Any]:
    """Query machine capacity for Ohio plant (BR-06, BR-07).

    Only Ohio capacity is tracked. Florida plant is offline.
    """
    table = db.get_table(settings.dynamodb_table_capacity)
    response = table.get_item(
        Key={"machine_type": input_data.machine_type, "plant": "Ohio"}
    )
    item = response.get("Item")
    if not item:
        return {
            "error": {
                "code": "NOT_FOUND",
                "message": f"Capacity data not found for {input_data.machine_type} at Ohio",
            }
        }
    return item


@log_tool_invocation
@tool_error_handler
async def get_workforce(settings: Settings, db: DynamoDBClient) -> dict[str, Any]:
    """Query Ohio plant workforce availability (BR-06).

    No input parameters required. Returns Ohio workforce data.
    """
    table = db.get_table(settings.dynamodb_table_workforce)
    response = table.get_item(Key={"plant": "Ohio"})
    item = response.get("Item")
    if not item:
        return {"error": {"code": "NOT_FOUND", "message": "Workforce data not found for Ohio"}}
    return item


@log_tool_invocation
@tool_error_handler
async def get_materials(
    input_data: Optional[GetMaterialsInput], settings: Settings, db: DynamoDBClient
) -> dict[str, Any]:
    """Query raw material inventory at Ohio plant (BR-08, BR-18).

    Optional filter by material_type. Returns all materials if no filter.
    """
    table = db.get_table(settings.dynamodb_table_materials)

    if input_data and input_data.material_type:
        response = table.get_item(
            Key={"material_type": input_data.material_type, "plant": "Ohio"}
        )
        item = response.get("Item")
        if not item:
            return {
                "error": {
                    "code": "NOT_FOUND",
                    "message": f"Material {input_data.material_type} not found at Ohio",
                }
            }
        return {"materials": [item]}

    # Scan for all Ohio materials (small table, scan is acceptable)
    response = table.scan(
        FilterExpression=Key("plant").eq("Ohio")
    )
    items = response.get("Items", [])
    return {"materials": items}
