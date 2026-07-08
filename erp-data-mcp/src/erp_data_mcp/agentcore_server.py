"""AgentCore-compatible MCP server entry point.

Uses FastMCP with streamable-http transport for deployment
on Bedrock AgentCore Runtime.
"""

from __future__ import annotations

import os
import sys

# Ensure the src/ directory is on sys.path so package imports resolve
_src_dir = os.path.join(os.path.dirname(__file__), os.pardir)
if os.path.abspath(_src_dir) not in sys.path:
    sys.path.insert(0, os.path.abspath(_src_dir))

import json  # noqa: E402
import logging  # noqa: E402

from mcp.server.fastmcp import FastMCP  # noqa: E402

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
from erp_data_mcp.tools.seed import reset_seed_data

logger = logging.getLogger("erp_data_mcp")

settings = Settings()
configure_logging(settings.log_level)
db = DynamoDBClient.get_instance(settings.aws_region)

mcp = FastMCP("erp-data-mcp", host="0.0.0.0", stateless_http=True, path="/mcp/")  # noqa: B104 - Required: AgentCore Runtime binds to all interfaces in container


@mcp.tool()
async def get_orders_tool(plant: str, status: str | None = None) -> str:
    """Query production orders by plant with optional status filter.

    Args:
        plant: Plant name — must be exactly "Florida" or "Ohio".
        status: Optional status filter — "Active", "Delayed", "Transferred", or "Cancelled".
    """
    result = await get_orders(GetOrdersInput(plant=plant, status=status), settings, db)
    return json.dumps(result, default=str)


@mcp.tool()
async def get_order_by_id_tool(order_id: str) -> str:
    """Retrieve a single production order by its ID."""
    result = await get_order_by_id(GetOrderByIdInput(order_id=order_id), settings, db)
    return json.dumps(result, default=str)


@mcp.tool()
async def update_order_priority_tool(order_id: str, priority: str) -> str:
    """Update priority classification (P1/P2/P3) for a Florida order.

    Args:
        order_id: Order ID in format PO-YYYY-NNN (e.g., PO-2026-001).
        priority: Priority level — must be "P1", "P2", or "P3".
    """
    result = await update_order_priority(
        UpdateOrderPriorityInput(order_id=order_id, priority=priority),
        settings, db,
    )
    return json.dumps(result, default=str)


@mcp.tool()
async def update_order_status_tool(order_id: str, status: str) -> str:
    """Update order status (Active/Delayed/Transferred/Cancelled).

    Args:
        order_id: Order ID in format PO-YYYY-NNN (e.g., PO-2026-001).
        status: New status — must be "Active", "Delayed", "Transferred", or "Cancelled".
    """
    result = await update_order_status(
        UpdateOrderStatusInput(order_id=order_id, status=status),
        settings, db,
    )
    return json.dumps(result, default=str)


@mcp.tool()
async def get_machine_capacity_tool(machine_type: str) -> str:
    """Query machine capacity data for Ohio plant (Rolling Mill or Finishing Line)."""
    result = await get_machine_capacity(
        GetMachineCapacityInput(machine_type=machine_type), settings, db,
    )
    return json.dumps(result, default=str)


@mcp.tool()
async def get_workforce_tool() -> str:
    """Query Ohio plant workforce availability."""
    result = await get_workforce(settings, db)
    return json.dumps(result, default=str)


@mcp.tool()
async def get_materials_tool(material_type: str | None = None) -> str:
    """Query raw material inventory at Ohio plant with optional material type filter."""
    inp = GetMaterialsInput(material_type=material_type) if material_type else None
    result = await get_materials(inp, settings, db)
    return json.dumps(result, default=str)


@mcp.tool()
async def get_customers_tool(customer_id: str | None = None) -> str:
    """Query customer data with optional customer ID filter."""
    inp = GetCustomersInput(customer_id=customer_id) if customer_id else None
    result = await get_customers(inp, settings, db)
    return json.dumps(result, default=str)


@mcp.tool()
async def get_running_tracker_tool(session_id: str) -> str:
    """Get current running capacity tracker for a workflow session."""
    result = await get_running_tracker(
        GetRunningTrackerInput(session_id=session_id), settings, db,
    )
    return json.dumps(result, default=str)


@mcp.tool()
async def update_running_tracker_tool(
    session_id: str,
    rolling_mill_normal_hrs: float | None = None,
    rolling_mill_overtime_hrs: float | None = None,
    rolling_mill_weekend_hrs: float | None = None,
    finishing_line_normal_hrs: float | None = None,
    finishing_line_overtime_hrs: float | None = None,
    finishing_line_weekend_hrs: float | None = None,
    material_surplus_tons: dict[str, float] | None = None,
    workforce_surplus: float | None = None,
    add_transferred: str | None = None,
    add_delayed: str | None = None,
    add_rejected: str | None = None,
) -> str:
    """Update running capacity tracker after a scheduling decision.

    Args:
        session_id: Workflow session ID (UUID v4).
        rolling_mill_normal_hrs: Updated Rolling Mill normal surplus hours.
        rolling_mill_overtime_hrs: Updated Rolling Mill overtime hours.
        rolling_mill_weekend_hrs: Updated Rolling Mill weekend hours.
        finishing_line_normal_hrs: Updated Finishing Line normal surplus hours.
        finishing_line_overtime_hrs: Updated Finishing Line overtime hours.
        finishing_line_weekend_hrs: Updated Finishing Line weekend hours.
        material_surplus_tons: Updated material surplus map (material_type -> tons).
        workforce_surplus: Updated workforce surplus count.
        add_transferred: Order ID to append to transferred list.
        add_delayed: Order ID to append to delayed list.
        add_rejected: Order ID to append to rejected list.
    """
    result = await update_running_tracker(
        UpdateRunningTrackerInput(
            session_id=session_id,
            rolling_mill_normal_hrs=rolling_mill_normal_hrs,
            rolling_mill_overtime_hrs=rolling_mill_overtime_hrs,
            rolling_mill_weekend_hrs=rolling_mill_weekend_hrs,
            finishing_line_normal_hrs=finishing_line_normal_hrs,
            finishing_line_overtime_hrs=finishing_line_overtime_hrs,
            finishing_line_weekend_hrs=finishing_line_weekend_hrs,
            material_surplus_tons=material_surplus_tons,
            workforce_surplus=workforce_surplus,
            add_transferred=add_transferred,
            add_delayed=add_delayed,
            add_rejected=add_rejected,
        ),
        settings, db,
    )
    return json.dumps(result, default=str)


@mcp.tool()
async def reset_seed_data_tool(mode: str) -> str:
    """Reset ERP data to a fresh seed state. Use 'demo' for a curated 16-order subset (faster) or 'full' for all 40 orders.

    Args:
        mode: Seed mode — must be "demo" or "full".
    """
    result = await reset_seed_data(mode, settings, db)
    return json.dumps(result, default=str)


if __name__ == "__main__":
    mcp.run(transport="streamable-http")
