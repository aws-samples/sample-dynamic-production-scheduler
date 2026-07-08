"""MCP Server entry point — registers 2 audit tools and starts stdio transport."""

from __future__ import annotations

import asyncio
import json
import logging

from pydantic import ValidationError

from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import TextContent, Tool

from audit_mcp.config import Settings
from audit_mcp.db.client import DynamoDBClient
from audit_mcp.logging_config import configure_logging
from audit_mcp.models.schemas import GetAuditTrailInput, WriteAuditEntryInput
from audit_mcp.tools.audit import get_audit_trail, write_audit_entry

logger = logging.getLogger("audit_mcp")

TOOL_DEFINITIONS = [
    Tool(
        name="write_audit_entry",
        description="Write a decision or action to the audit trail",
        inputSchema=WriteAuditEntryInput.model_json_schema(),
    ),
    Tool(
        name="get_audit_trail",
        description="Read audit entries for a session with optional agent and time filters",
        inputSchema=GetAuditTrailInput.model_json_schema(),
    ),
]


def create_server() -> tuple[Server, Settings, DynamoDBClient]:
    """Create and configure the MCP server with audit tools registered."""
    settings = Settings()
    configure_logging(settings.log_level)
    db = DynamoDBClient.get_instance(settings.aws_region)

    app = Server("audit-mcp")

    @app.list_tools()
    async def handle_list_tools() -> list[Tool]:
        return TOOL_DEFINITIONS

    @app.call_tool()
    async def handle_call_tool(name: str, arguments: dict) -> list[TextContent]:
        handler_map = {
            "write_audit_entry": lambda args: write_audit_entry(
                WriteAuditEntryInput(**args), settings, db
            ),
            "get_audit_trail": lambda args: get_audit_trail(
                GetAuditTrailInput(**args), settings, db
            ),
        }

        handler = handler_map.get(name)
        if not handler:
            return [TextContent(
                type="text",
                text=json.dumps({"error": {"code": "NOT_FOUND", "message": f"Unknown tool: {name}"}}),
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
