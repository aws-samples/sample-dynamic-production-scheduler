"""Impact Assessment Agent entry point.

Initializes Strands Agent with Claude 4.5 Haiku, registers MCP tools
(via AgentCore Gateway) and Python tools (scoring engine), and exposes
the fail-closed invocation wrapper (Pattern 7).
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from typing import Any

from strands import Agent, tool
from strands.models.bedrock import BedrockModel
from strands.tools.mcp import MCPClient

from impact_assessment_agent.config import AgentSettings
from impact_assessment_agent.logging_config import configure_logging
from impact_assessment_agent.models.schemas import (
    ImpactAssessmentOutput,
    PriorityThresholds,
    ScoringWeights,
)
from impact_assessment_agent.prompts.system_prompt import get_full_system_prompt
from impact_assessment_agent.scoring import (
    build_explanation as _build_explanation,
    build_group_tables as _build_group_tables,
    build_priority_summary as _build_priority_summary,
    reclassify_order as _reclassify_order,
    score_orders as _score_orders,
)

logger = logging.getLogger("impact_assessment_agent")


# -------------------------------------------------------------------
# Result container
# -------------------------------------------------------------------

@dataclass
class AgentResult:
    """Wrapper for agent invocation results."""

    success: bool
    data: Any = None
    error: str | None = None
    raw_output: Any = None


# -------------------------------------------------------------------
# Python tools — registered with Strands @tool decorator
# The LLM calls these after fetching data via MCP tools.
# -------------------------------------------------------------------

# Module-level settings (populated by create_agent)
_settings: AgentSettings | None = None
_staged_data: dict[str, Any] = {}


def _get_weights() -> ScoringWeights:
    """Return scoring weights from current settings."""
    assert _settings is not None, "Agent not initialized"
    return _settings.get_scoring_weights()


def _get_thresholds() -> PriorityThresholds:
    """Return priority thresholds from current settings."""
    assert _settings is not None, "Agent not initialized"
    return _settings.get_priority_thresholds()


@tool
def stage_erp_data(orders_json: str, customers_json: str) -> str:
    """Stage fetched ERP data for subsequent scoring tools.

    Call this ONCE after fetching orders and customers via MCP tools.
    Subsequent scoring tools will read from staged data automatically
    — no need to pass large JSON strings again.

    Args:
        orders_json: JSON string of orders from get_orders MCP tool.
        customers_json: JSON string of customers from get_customers MCP tool.
    """
    global _staged_data
    orders = json.loads(orders_json)
    customers_raw = json.loads(customers_json)
    if isinstance(customers_raw, list):
        customers = {c["customer_id"]: c for c in customers_raw}
    else:
        customers = customers_raw
    _staged_data = {"orders": orders, "customers": customers}
    return json.dumps({
        "status": "staged",
        "orders_count": len(orders),
        "customers_count": len(customers),
    })


@tool
def score_orders_tool(orders_json: str = "", customers_json: str = "") -> str:
    """Score and classify production orders by priority.

    Runs the deterministic scoring algorithm on orders fetched from ERP.
    Returns JSON array of scored orders sorted by priority.

    If orders_json and customers_json are empty, reads from staged data
    (call stage_erp_data first). Otherwise uses provided JSON strings.

    Args:
        orders_json: JSON string of orders (optional if data is staged).
        customers_json: JSON string of customers (optional if data is staged).
    """
    if orders_json and customers_json:
        orders = json.loads(orders_json)
        customers_raw = json.loads(customers_json)
        if isinstance(customers_raw, list):
            customers = {c["customer_id"]: c for c in customers_raw}
        else:
            customers = customers_raw
    elif _staged_data:
        orders = _staged_data["orders"]
        customers = _staged_data["customers"]
    else:
        return json.dumps({"error": "No data available. Call stage_erp_data first or provide JSON arguments."})

    scored = _score_orders(
        orders, customers, _get_weights(), _get_thresholds()
    )
    return json.dumps([o.model_dump() for o in scored], default=str)


@tool
def reclassify_order_tool(
    scored_orders_json: str, order_id: str, new_priority: str
) -> str:
    """Override an order's priority and re-evaluate non-pinned orders.

    Args:
        scored_orders_json: JSON string of previously scored orders.
        order_id: The order ID to override (e.g. PO-2026-001).
        new_priority: New priority level (P1, P2, or P3).
    """
    from impact_assessment_agent.models.schemas import ScoredOrder

    raw = json.loads(scored_orders_json)
    scored = [ScoredOrder.model_validate(o) for o in raw]
    overridden, changed = _reclassify_order(
        scored, order_id, new_priority, _get_weights(), _get_thresholds()
    )
    return json.dumps(
        {
            "overridden": overridden.model_dump(),
            "changed_orders": [o.model_dump() for o in changed],
        },
        default=str,
    )


@tool
def get_priority_summary(scored_orders_json: str) -> str:
    """Generate a priority distribution summary from scored orders.

    Args:
        scored_orders_json: JSON string of scored orders.
    """
    from impact_assessment_agent.models.schemas import ScoredOrder

    raw = json.loads(scored_orders_json)
    scored = [ScoredOrder.model_validate(o) for o in raw]
    summary = _build_priority_summary(scored)
    return json.dumps(summary.model_dump(), default=str)


@tool
def explain_classification(scored_order_json: str) -> str:
    """Generate a detailed explanation for a single order's classification.

    Args:
        scored_order_json: JSON string of a single scored order.
    """
    from impact_assessment_agent.models.schemas import ScoredOrder

    order = ScoredOrder.model_validate(json.loads(scored_order_json))
    explanation = _build_explanation(order, _get_weights())
    return json.dumps(explanation.model_dump(), default=str)


@tool
def get_group_tables(scored_orders_json: str) -> str:
    """Build grouped tables for P1/P2/P3 presentation.

    Args:
        scored_orders_json: JSON string of scored orders.
    """
    from impact_assessment_agent.models.schemas import ScoredOrder

    raw = json.loads(scored_orders_json)
    scored = [ScoredOrder.model_validate(o) for o in raw]
    tables = _build_group_tables(scored)
    return json.dumps([t.model_dump() for t in tables], default=str)


# -------------------------------------------------------------------
# MCP client factory
# -------------------------------------------------------------------

def _get_oauth_token(token_endpoint: str, client_id: str, client_secret: str, scopes: list[str]) -> str:
    """Obtain OAuth2 token from Cognito using client_credentials grant."""
    import base64
    import httpx
    auth = base64.b64encode(f"{client_id}:{client_secret}".encode()).decode()
    resp = httpx.post(
        token_endpoint,
        headers={"Authorization": f"Basic {auth}", "Content-Type": "application/x-www-form-urlencoded"},
        data={"grant_type": "client_credentials", "scope": " ".join(scopes)},
    )
    resp.raise_for_status()
    return resp.json()["access_token"]


def _create_mcp_client(gateway_url: str, token_endpoint: str, client_id: str, client_secret: str, scopes: list[str]) -> tuple[MCPClient, list]:
    """Create MCPClient, enter context, and return (client, tools).

    Follows the AWS reference pattern: get token once, create client,
    explicitly enter context manager, list tools, pass tools to Agent.
    """
    from mcp.client.streamable_http import streamablehttp_client

    token = _get_oauth_token(token_endpoint, client_id, client_secret, scopes)
    headers = {"Authorization": f"Bearer {token}"}

    mcp_client = MCPClient(
        lambda: streamablehttp_client(url=gateway_url, headers=headers)
    )
    mcp_client.__enter__()
    tools = mcp_client.list_tools_sync()
    logger.info("MCP client connected, loaded %d tools", len(tools))
    return mcp_client, tools


# -------------------------------------------------------------------
# Agent factory
# -------------------------------------------------------------------

PYTHON_TOOLS = [
    stage_erp_data,
    score_orders_tool,
    reclassify_order_tool,
    get_priority_summary,
    explain_classification,
    get_group_tables,
]


_mcp_client_cached: MCPClient | None = None
_mcp_tools_cached: list | None = None
_oauth_token_cached: str | None = None
_oauth_token_expiry: float = 0


def _get_or_create_mcp_client(settings: AgentSettings) -> tuple[MCPClient, list]:
    """Return cached MCP client and tools, creating if needed.

    Caches the MCP connection and OAuth token across invocations to
    avoid the 2-3s overhead of token fetch + Gateway handshake per request.
    Token is refreshed 5 minutes before expiry.
    """
    global _mcp_client_cached, _mcp_tools_cached, _oauth_token_cached, _oauth_token_expiry
    import time as _time

    now = _time.time()
    # Refresh if token expires within 5 minutes or no client exists
    if _mcp_client_cached is not None and _mcp_tools_cached is not None and now < _oauth_token_expiry - 300:
        return _mcp_client_cached, _mcp_tools_cached

    # Close old client if refreshing
    if _mcp_client_cached is not None:
        try:
            _mcp_client_cached.__exit__(None, None, None)
        except Exception:
            pass

    logger.info("Creating/refreshing MCP client and OAuth token")
    _mcp_client_cached, _mcp_tools_cached = _create_mcp_client(
        settings.gateway_url, settings.cognito_token_endpoint,
        settings.cognito_client_id, settings.cognito_client_secret,
        [settings.erp_data_scope],
    )
    # Cognito tokens are typically valid for 1 hour
    _oauth_token_expiry = now + 3600
    return _mcp_client_cached, _mcp_tools_cached


def create_agent(settings: AgentSettings | None = None, session_id: str = "") -> Agent:
    """Initialize and return a configured Strands Agent.

    Args:
        settings: Optional AgentSettings. Loaded from env if None.
        session_id: Session ID for AgentCore Memory persistence.

    Returns:
        Configured Agent instance with MCP + Python tools.
    """
    global _settings, _staged_data
    _settings = settings or AgentSettings()
    _staged_data = {}

    configure_logging(_settings.log_level)
    logger.info(
        "Initializing Impact Assessment Agent",
        extra={"model": _settings.bedrock_model_id},
    )

    model = BedrockModel(
        model_id=_settings.bedrock_model_id,
        max_tokens=16384,
        temperature=0,
    )

    mcp_client, mcp_tools = _get_or_create_mcp_client(_settings)

    # AgentCore Memory session manager
    session_manager = None
    if _settings.agentcore_memory_id and session_id:
        try:
            from bedrock_agentcore.memory.integrations.strands.config import (
                AgentCoreMemoryConfig,
            )
            from bedrock_agentcore.memory.integrations.strands.session_manager import (
                AgentCoreMemorySessionManager,
            )
            # filter_restored_tool_context=True strips toolUse/toolResult blocks
            # when restoring messages from Memory, preventing the orphaned-block
            # corruption that occurs when AgentCore retries long-running invocations.
            memory_config = AgentCoreMemoryConfig(
                memory_id=_settings.agentcore_memory_id,
                session_id=session_id,
                actor_id="impact_assessment",
                filter_restored_tool_context=True,
            )
            session_manager = AgentCoreMemorySessionManager(
                agentcore_memory_config=memory_config,
                region_name="us-east-1",
            )
            logger.info("AgentCore Memory enabled with tool block filtering", extra={"session_id": session_id})
        except Exception:
            logger.warning("AgentCore Memory init failed, continuing without memory", exc_info=True)

    agent = Agent(
        model=model,
        system_prompt=get_full_system_prompt(),
        tools=mcp_tools + PYTHON_TOOLS,
        structured_output_model=ImpactAssessmentOutput,
        **({"session_manager": session_manager} if session_manager else {}),
    )

    logger.info("Impact Assessment Agent initialized")
    return agent


# -------------------------------------------------------------------
# Fail-closed invocation wrapper (Pattern 7)
# -------------------------------------------------------------------

def run_agent(agent: Agent, task: str, session_id: str) -> AgentResult:
    """Invoke the agent with fail-closed error handling.

    On any unhandled exception the wrapper returns an error result
    instead of propagating — classification is all-or-nothing.

    Args:
        agent: Configured Strands Agent instance.
        task: Natural language task for the agent.
        session_id: Correlation ID for logging and audit.

    Returns:
        AgentResult with success/failure and data or error message.
    """
    try:
        logger.info(
            "Agent invoked",
            extra={"session_id": session_id, "task_length": len(task)},
        )
        result = agent(task)
        logger.info(
            "Agent completed",
            extra={"session_id": session_id},
        )
        return AgentResult(success=True, data=str(result), raw_output=result)
    except Exception:
        logger.error(
            "Agent failed — returning error result",
            extra={"session_id": session_id},
            exc_info=True,
        )
        return AgentResult(
            success=False,
            error="Impact Assessment Agent encountered an error",
        )
