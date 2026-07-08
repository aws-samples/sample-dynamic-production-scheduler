"""MCP Server entry point — registers all 10 tools and starts stdio transport."""

from __future__ import annotations

import asyncio
import logging

from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import TextContent, Tool

from erp_data_mcp.config import Settings
from erp_data_mcp.db.client import DynamoDBClient
from erp_data_mcp.logging_config import configure_logging
from erp_data_mcp.models.schemas import (
    GetCustomersInput,
    GetMachineCapacityInput,
    GetMaterialsInput,
    GetOrderByIdInput,
    GetOrdersInput,
    GetRunningTrackerInput,
    UpdateOrderPriorityInput,
    UpdateOrderStatusInput,
    UpdateRunningTrackerInput,
)
from erp_data_mcp.tools.capacity import get_machine_capacity, get_workforce, get_materials
from erp_data_mcp.tools.customers import get_customers
from erp_data_mcp.tools.orders import (
    get_order_by_id,
    get_orders,
    update_order_priority,
    update_order_status,
)
from erp_data_mcp.tools.tracker import get_running_tracker, update_running_tracker

logger = logging.getLogger("erp_data_mcp")


# Tool definitions for MCP list_tools
TOOL_DEFINITIONS = [
    Tool(
        name="get_orders",
        description="Query production orders by plant with optional status filter",
        inputSchema=GetOrdersInput.model_json_schema(),
    ),
    Tool(
        name="get_order_by_id",
        description="Retrieve a single production order by its ID",
        inputSchema=GetOrderByIdInput.model_json_schema(),
    ),
    Tool(
        name="update_order_priority",
        description="Update priority classification (P1/P2/P3) for a Florida order",
        inputSchema=UpdateOrderPriorityInput.model_json_schema(),
    ),
    Tool(
        name="update_order_status",
        description="Update order status (Active/Delayed/Transferred/Cancelled)",
        inputSchema=UpdateOrderStatusInput.model_json_schema(),
    ),
    Tool(
        name="get_machine_capacity",
        description="Query machine capacity data for Ohio plant (Rolling Mill or Finishing Line)",
        inputSchema=GetMachineCapacityInput.model_json_schema(),
    ),
    Tool(
        name="get_workforce",
        description="Query Ohio plant workforce availability",
        inputSchema={"type": "object", "properties": {}, "required": []},
    ),
    Tool(
        name="get_materials",
        description="Query raw material inventory at Ohio plant with optional material type filter",
        inputSchema=GetMaterialsInput.model_json_schema(),
    ),
    Tool(
        name="get_customers",
        description="Query customer data with optional customer ID filter",
        inputSchema=GetCustomersInput.model_json_schema(),
    ),
    Tool(
        name="get_running_tracker",
        description="Get current running capacity tracker for a workflow session",
        inputSchema=GetRunningTrackerInput.model_json_schema(),
    ),
    Tool(
        name="update_running_tracker",
        description="Update running capacity tracker after a scheduling decision",
        inputSchema=UpdateRunningTrackerInput.model_json_schema(),
    ),
]


def create_server() -> tuple[Server, Settings, DynamoDBClient]:
    """Create and configure the MCP server with all tools registered.

    Returns:
        Tuple of (server, settings, db_client).
    """
    settings = Settings()
    configure_logging(settings.log_level)
    db = DynamoDBClient.get_instance(settings.aws_region)

    app = Server("erp-data-mcp")

    @app.list_tools()
    async def handle_list_tools() -> list[Tool]:
        return TOOL_DEFINITIONS

    @app.call_tool()
    async def handle_call_tool(name: str, arguments: dict) -> list[TextContent]:
        import json
        from pydantic import ValidationError

        handler_map = {
            "get_orders": lambda args: get_orders(
                GetOrdersInput(**args), settings, db
            ),
            "get_order_by_id": lambda args: get_order_by_id(
                GetOrderByIdInput(**args), settings, db
            ),
            "update_order_priority": lambda args: update_order_priority(
                UpdateOrderPriorityInput(**args), settings, db
            ),
            "update_order_status": lambda args: update_order_status(
                UpdateOrderStatusInput(**args), settings, db
            ),
            "get_machine_capacity": lambda args: get_machine_capacity(
                GetMachineCapacityInput(**args), settings, db
            ),
            "get_workforce": lambda _args: get_workforce(settings, db),
            "get_materials": lambda args: get_materials(
                GetMaterialsInput(**args) if args else None, settings, db
            ),
            "get_customers": lambda args: get_customers(
                GetCustomersInput(**args) if args else None, settings, db
            ),
            "get_running_tracker": lambda args: get_running_tracker(
                GetRunningTrackerInput(**args), settings, db
            ),
            "update_running_tracker": lambda args: update_running_tracker(
                UpdateRunningTrackerInput(**args), settings, db
            ),
        }

        handler = handler_map.get(name)
        if not handler:
            return [TextContent(
                type="text",
                text=json.dumps({"error": {"code": "NOT_FOUND", "message": f"Unknown tool: {name}"}})
            )]

        try:
            result = await handler(arguments or {})
            return [TextContent(type="text", text=json.dumps(result, default=str))]
        except ValidationError as ve:
            error_details = []
            for err in ve.errors():
                field = ".".join(str(loc) for loc in err["loc"])
                error_details.append(f"{field}: {err['msg']}")
            return [TextContent(
                type="text",
                text=json.dumps({
                    "error": {
                        "code": "VALIDATION_ERROR",
                        "message": f"Invalid parameters for tool '{name}'",
                        "details": error_details,
                    }
                })
            )]
        except Exception as exc:
            logger.error(f"Tool {name} failed: {exc}", exc_info=True)
            return [TextContent(
                type="text",
                text=json.dumps({
                    "error": {
                        "code": "INTERNAL_ERROR",
                        "message": f"Tool '{name}' encountered an error: {str(exc)}",
                    }
                })
            )]

    return app, settings, db


async def run_server() -> None:
    """Start the MCP server with stdio transport."""
    app, _, _ = create_server()
    async with stdio_server() as (read_stream, write_stream):
        await app.run(read_stream, write_stream, app.create_initialization_options())


def main() -> None:
    """CLI entry point."""
    asyncio.run(run_server())


if __name__ == "__main__":
    main()
