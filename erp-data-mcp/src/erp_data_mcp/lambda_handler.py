"""AWS Lambda handler for AgentCore Gateway MCP tool calls.

Receives tool invocations from AgentCore Gateway, validates inputs via
Pydantic schemas (SECURITY-05), dispatches to existing async tool functions,
and returns JSON-serialisable MCP-compatible responses.

AgentCore Gateway sends the tool's arguments dict directly as the Lambda event.
Routing is done via the 'action_name' property included in each tool's inputSchema.

SECURITY-03: Structured logging with request_id correlation.
SECURITY-09: Generic error messages — no stack traces exposed.
SECURITY-12: No hardcoded credentials — Settings from env vars.
SECURITY-15: Global error handler, fail-closed on any exception.
"""

from __future__ import annotations

import asyncio
import json
import logging
from typing import Any, Callable

from erp_data_mcp.config import Settings
from erp_data_mcp.db.client import DynamoDBClient
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
logger.setLevel(logging.INFO)

# ---------------------------------------------------------------------------
# Initialise shared resources outside handler for Lambda connection reuse
# SECURITY-12: Settings loaded from environment variables, no hardcoded creds
# ---------------------------------------------------------------------------
settings = Settings()
db = DynamoDBClient.get_instance(settings.aws_region)


# ---------------------------------------------------------------------------
# Async helper — run coroutines from synchronous Lambda entry point
# ---------------------------------------------------------------------------

def _run_async(coro: Any) -> Any:
    """Execute an async coroutine from the synchronous Lambda handler."""
    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


# ---------------------------------------------------------------------------
# Per-tool dispatch handlers
# Each validates input via Pydantic (SECURITY-05) then delegates to the
# existing async tool function.
# ---------------------------------------------------------------------------

def _handle_get_orders(event: dict[str, Any]) -> Any:
    validated = GetOrdersInput(**{k: v for k, v in event.items() if k != "action_name"})
    return _run_async(get_orders(validated, settings, db))


def _handle_get_order_by_id(event: dict[str, Any]) -> Any:
    validated = GetOrderByIdInput(**{k: v for k, v in event.items() if k != "action_name"})
    return _run_async(get_order_by_id(validated, settings, db))


def _handle_update_order_priority(event: dict[str, Any]) -> Any:
    validated = UpdateOrderPriorityInput(**{k: v for k, v in event.items() if k != "action_name"})
    return _run_async(update_order_priority(validated, settings, db))


def _handle_update_order_status(event: dict[str, Any]) -> Any:
    validated = UpdateOrderStatusInput(**{k: v for k, v in event.items() if k != "action_name"})
    return _run_async(update_order_status(validated, settings, db))


def _handle_get_machine_capacity(event: dict[str, Any]) -> Any:
    validated = GetMachineCapacityInput(**{k: v for k, v in event.items() if k != "action_name"})
    return _run_async(get_machine_capacity(validated, settings, db))


def _handle_get_workforce(event: dict[str, Any]) -> Any:
    # get_workforce takes no input schema — only settings and db
    return _run_async(get_workforce(settings, db))


def _handle_get_materials(event: dict[str, Any]) -> Any:
    args = {k: v for k, v in event.items() if k != "action_name"}
    validated = GetMaterialsInput(**args) if args else None
    return _run_async(get_materials(validated, settings, db))


def _handle_get_customers(event: dict[str, Any]) -> Any:
    args = {k: v for k, v in event.items() if k != "action_name"}
    validated = GetCustomersInput(**args) if args else None
    return _run_async(get_customers(validated, settings, db))


def _handle_get_running_tracker(event: dict[str, Any]) -> Any:
    validated = GetRunningTrackerInput(**{k: v for k, v in event.items() if k != "action_name"})
    return _run_async(get_running_tracker(validated, settings, db))


def _handle_update_running_tracker(event: dict[str, Any]) -> Any:
    validated = UpdateRunningTrackerInput(**{k: v for k, v in event.items() if k != "action_name"})
    return _run_async(update_running_tracker(validated, settings, db))


def _handle_reset_seed_data(event: dict[str, Any]) -> Any:
    mode = event.get("mode", "full")
    return _run_async(reset_seed_data(mode, settings, db))


# ---------------------------------------------------------------------------
# Tool dispatch registry — keyed by action_name values
# ---------------------------------------------------------------------------

TOOL_DISPATCH: dict[str, Callable[[dict[str, Any]], Any]] = {
    "get_orders_tool": _handle_get_orders,
    "get_order_by_id_tool": _handle_get_order_by_id,
    "update_order_priority_tool": _handle_update_order_priority,
    "update_order_status_tool": _handle_update_order_status,
    "get_machine_capacity_tool": _handle_get_machine_capacity,
    "get_workforce_tool": _handle_get_workforce,
    "get_materials_tool": _handle_get_materials,
    "get_customers_tool": _handle_get_customers,
    "get_running_tracker_tool": _handle_get_running_tracker,
    "update_running_tracker_tool": _handle_update_running_tracker,
    "reset_seed_data_tool": _handle_reset_seed_data,
}


# ---------------------------------------------------------------------------
# Lambda entry point
# SECURITY-15: Global error handler — fail-closed on any exception
# ---------------------------------------------------------------------------

def handler(event: dict[str, Any], context: Any) -> dict[str, Any]:
    """AWS Lambda handler for AgentCore Gateway MCP tool calls.

    AgentCore Gateway passes the tool's arguments dict directly as the
    Lambda event. Routing uses the 'action_name' property that each tool
    declares in its inputSchema (following the AWS reference pattern).

    Event shape example:
        {"action_name": "get_orders_tool", "plant": "Florida", "status": "Active"}

    Returns:
        {"result": <tool_output>}  on success
        {"error": "<message>"}     on failure (generic — SECURITY-09)
    """
    request_id = getattr(context, "aws_request_id", "unknown")

    # SECURITY-03: Structured logging with request_id correlation
    logger.info(
        "Received tool invocation",
        extra={"request_id": request_id, "event_keys": list(event.keys())},
    )

    try:
        # Gateway sends arguments dict as event; action_name is the routing key
        action_name = event.get("action_name")

        if not action_name:
            logger.warning("Missing action_name in event", extra={"request_id": request_id})
            return {"error": "Missing action_name in request"}

        if action_name not in TOOL_DISPATCH:
            logger.warning(
                "Unknown action requested",
                extra={"request_id": request_id, "action_name": action_name},
            )
            return {"error": f"Unknown action: {action_name}"}

        logger.info(
            "Dispatching tool",
            extra={"request_id": request_id, "action_name": action_name},
        )

        result = TOOL_DISPATCH[action_name](event)

        # Ensure result is JSON-serialisable (handle Decimal, datetime, etc.)
        serialised = json.loads(json.dumps(result, default=str))

        logger.info(
            "Tool execution succeeded",
            extra={"request_id": request_id, "action_name": action_name},
        )
        return {"result": serialised}

    except (ValueError, TypeError, KeyError) as exc:
        # Pydantic validation errors and argument issues — client error
        logger.warning(
            "Input validation failed",
            extra={"request_id": request_id, "error": str(exc)},
        )
        return {"error": f"Invalid input: {exc}"}

    except Exception:
        # SECURITY-09: Never expose stack traces to caller
        # SECURITY-15: Fail-closed — return error, log details server-side
        logger.error(
            "Tool execution failed",
            extra={"request_id": request_id},
            exc_info=True,
        )
        return {"error": "Internal server error"}
