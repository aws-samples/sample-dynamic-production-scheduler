"""AWS Lambda handler for AgentCore Gateway MCP tool calls (audit-mcp).

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

from audit_mcp.config import Settings
from audit_mcp.db.client import DynamoDBClient
from audit_mcp.models.schemas import GetAuditTrailInput, WriteAuditEntryInput
from audit_mcp.tools.audit import get_audit_trail, write_audit_entry

logger = logging.getLogger("audit_mcp")
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

def _handle_write_audit_entry(event: dict[str, Any]) -> Any:
    args = {k: v for k, v in event.items() if k != "action_name"}
    validated = WriteAuditEntryInput(**args)
    return _run_async(write_audit_entry(validated, settings, db))


def _handle_get_audit_trail(event: dict[str, Any]) -> Any:
    args = {k: v for k, v in event.items() if k != "action_name"}
    validated = GetAuditTrailInput(**args)
    return _run_async(get_audit_trail(validated, settings, db))


# ---------------------------------------------------------------------------
# Tool dispatch registry — keyed by action_name values
# ---------------------------------------------------------------------------

TOOL_DISPATCH: dict[str, Callable[[dict[str, Any]], Any]] = {
    "write_audit_entry_tool": _handle_write_audit_entry,
    "get_audit_trail_tool": _handle_get_audit_trail,
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
        {"action_name": "get_audit_trail_tool", "session_id": "abc-123"}

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
