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
from typing import Optional  # noqa: E402

from mcp.server.fastmcp import FastMCP  # noqa: E402

from audit_mcp.config import Settings
from audit_mcp.db.client import DynamoDBClient
from audit_mcp.logging_config import configure_logging
from audit_mcp.models.schemas import GetAuditTrailInput, WriteAuditEntryInput
from audit_mcp.tools.audit import get_audit_trail, write_audit_entry

logger = logging.getLogger("audit_mcp")

settings = Settings()
configure_logging(settings.log_level)
db = DynamoDBClient.get_instance(settings.aws_region)

mcp = FastMCP("audit-mcp", host="0.0.0.0", stateless_http=True, path="/mcp/")  # noqa: B104 - Required: AgentCore Runtime binds to all interfaces in container


@mcp.tool()
async def write_audit_entry_tool(
    session_id: str,
    agent: str,
    action: str,
    details: dict,
    timestamp: str,
) -> str:
    """Write a decision or action to the audit trail."""
    result = await write_audit_entry(
        WriteAuditEntryInput(
            session_id=session_id,
            agent=agent,
            action=action,
            details=details,
            timestamp=timestamp,
        ),
        settings,
        db,
    )
    return json.dumps(result, default=str)


@mcp.tool()
async def get_audit_trail_tool(
    session_id: str,
    agent: Optional[str] = None,
    start_time: Optional[str] = None,
) -> str:
    """Read audit entries for a session with optional agent and time filters."""
    result = await get_audit_trail(
        GetAuditTrailInput(
            session_id=session_id,
            agent=agent,
            start_time=start_time,
        ),
        settings,
        db,
    )
    return json.dumps(result, default=str)


if __name__ == "__main__":
    mcp.run(transport="streamable-http")
