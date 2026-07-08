"""Customer tool handlers — query customer data."""

from __future__ import annotations

import logging
from typing import Any, Optional

from erp_data_mcp.config import Settings
from erp_data_mcp.db.client import DynamoDBClient
from erp_data_mcp.decorators import log_tool_invocation, tool_error_handler
from erp_data_mcp.models.schemas import GetCustomersInput

logger = logging.getLogger("erp_data_mcp")


@log_tool_invocation
@tool_error_handler
async def get_customers(
    input_data: Optional[GetCustomersInput], settings: Settings, db: DynamoDBClient
) -> dict[str, Any]:
    """Query customer data with optional customer_id filter (BR-12, BR-18).

    Returns all customers if no filter provided.
    """
    table = db.get_table(settings.dynamodb_table_customers)

    if input_data and input_data.customer_id:
        response = table.get_item(Key={"customer_id": input_data.customer_id})
        item = response.get("Item")
        if not item:
            return {
                "error": {
                    "code": "NOT_FOUND",
                    "message": f"Customer {input_data.customer_id} not found",
                }
            }
        return {"customers": [item]}

    response = table.scan()
    items = response.get("Items", [])
    return {"customers": items}
