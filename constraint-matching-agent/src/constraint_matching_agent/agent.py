"""Constraint Matching Agent entry point.

Initializes Strands Agent with Claude 4.5 Haiku, registers MCP tools
(via AgentCore Gateway) and Python tools (funnel engine + tracker),
and exposes the fail-closed invocation wrapper (Pattern 7).
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from typing import Any

from strands import Agent, tool
from strands.models.bedrock import BedrockModel
from strands.tools.mcp import MCPClient

from constraint_matching_agent.config import AgentSettings
from constraint_matching_agent.funnel import (
    evaluate_funnel as _evaluate_funnel,
    simulate_cascade as _simulate_cascade,
)
from constraint_matching_agent.logging_config import configure_logging
from constraint_matching_agent.models.schemas import (
    AgentConfig,
    ConstraintMatchingOutput,
    RunningCapacityTracker,
)
from constraint_matching_agent.prompts.system_prompt import (
    get_full_system_prompt,
)
from constraint_matching_agent.tracker import TrackerState

logger = logging.getLogger("constraint_matching_agent")


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
# Module-level settings (populated by create_agent)
# -------------------------------------------------------------------

_settings: AgentSettings | None = None
_staged_data: dict[str, Any] = {}
_current_session_id: str = ""


def _get_config() -> AgentConfig:
    """Return AgentConfig from current settings."""
    assert _settings is not None, "Agent not initialized"
    return _settings.get_agent_config()


# -------------------------------------------------------------------
# Python tools — registered with Strands @tool decorator
# -------------------------------------------------------------------


@tool
def stage_erp_data(
    order_json: str,
    equipment_json: str,
    materials_json: str,
    workforce_json: str,
    receiving_plant_orders_json: str,
) -> str:
    """Stage fetched ERP data for subsequent constraint funnel tools.

    Call this ONCE after fetching all data via MCP tools.
    Subsequent tools (evaluate_funnel_tool) will read from staged data
    automatically — no need to pass large JSON strings again.

    Args:
        order_json: JSON of the disrupted plant order dict.
        equipment_json: JSON array of equipment capabilities.
        materials_json: JSON of material inventory.
        workforce_json: JSON of workforce data.
        receiving_plant_orders_json: JSON array of receiving plant active orders.
    """
    global _staged_data
    _staged_data = {
        "order": json.loads(order_json),
        "equipment": json.loads(equipment_json),
        "materials": json.loads(materials_json),
        "workforce": json.loads(workforce_json),
        "receiving_plant_orders": json.loads(receiving_plant_orders_json),
    }
    # If the LLM passed a list of orders instead of a single order, store
    # the list separately so evaluate_funnel_tool can iterate over them.
    order_data = _staged_data["order"]
    if isinstance(order_data, list):
        _staged_data["all_orders"] = order_data
        _staged_data["order"] = order_data[0] if order_data else {}
        return json.dumps({
            "status": "staged",
            "note": f"Received {len(order_data)} orders. First order staged: {order_data[0].get('order_id', 'unknown') if order_data else 'none'}. Call evaluate_funnel_tool once per order, passing order_json for each.",
            "order_count": len(order_data),
            "order_ids": [o.get("order_id", "") for o in order_data[:20]],
            "equipment_count": len(_staged_data["equipment"]) if isinstance(_staged_data["equipment"], list) else 1,
            "receiving_plant_orders_count": len(_staged_data["receiving_plant_orders"]) if isinstance(_staged_data["receiving_plant_orders"], list) else 0,
        })
    return json.dumps({
        "status": "staged",
        "order_id": order_data.get("order_id", "unknown"),
        "equipment_count": len(_staged_data["equipment"]) if isinstance(_staged_data["equipment"], list) else 1,
        "receiving_plant_orders_count": len(_staged_data["receiving_plant_orders"]) if isinstance(_staged_data["receiving_plant_orders"], list) else 0,
    })


@tool
def initialize_tracker_from_capacity(
    session_id: str = "",
    capacity_json: str = "",
) -> str:
    """Initialize the RunningCapacityTracker from CO agent capacity data.

    Reads the round1_co output from DynamoDB workflow-state if capacity_json
    is empty. Builds a tracker with correct surplus hours per shift tier.

    Args:
        session_id: Session ID to read CO data from DynamoDB (optional — uses
            the agent's current session ID if empty or if the provided ID
            fails to find data).
        capacity_json: Optional JSON of CO capacity snapshot (skips DynamoDB read).
    """
    import boto3
    from datetime import datetime

    # Prefer the agent's actual session ID over LLM-provided values,
    # which are often hallucinated (e.g. "workflow-session-001").
    effective_session_id = _current_session_id or session_id

    co_data = None
    if capacity_json:
        co_data = json.loads(capacity_json)
    else:
        try:
            ddb = boto3.resource("dynamodb", region_name="us-east-1")
            table = ddb.Table("disruptionai-workflow-state")
            # Try the effective session_id first, then the LLM-provided one
            for sid in [effective_session_id, session_id]:
                if sid and sid != effective_session_id:
                    # Only try the second ID if it's different
                    pass
                if sid:
                    resp = table.get_item(Key={"session_id": sid, "state_key": "round1_co"})
                    item = resp.get("Item")
                    if item:
                        co_data = item.get("data", {})
                        logger.info("Tracker init: found CO data for session=%s", sid)
                        break
            # Also try the LLM-provided session_id if different and not yet found
            if not co_data and session_id and session_id != effective_session_id:
                resp = table.get_item(Key={"session_id": session_id, "state_key": "round1_co"})
                item = resp.get("Item")
                if item:
                    co_data = item.get("data", {})
                    logger.info("Tracker init: found CO data for LLM session=%s", session_id)
            # Fallback: scan for most recent round1_co by TTL
            if not co_data:
                from boto3.dynamodb.conditions import Key as DKey
                scan_resp = table.scan(
                    FilterExpression=DKey("state_key").eq("round1_co"),
                    ProjectionExpression="session_id, #d, #t",
                    ExpressionAttributeNames={"#d": "data", "#t": "ttl"},
                )
                items = scan_resp.get("Items", [])
                if items:
                    latest = max(items, key=lambda x: x.get("ttl", 0))
                    co_data = latest.get("data", {})
                    logger.info("Tracker init: used fallback scan, session=%s", latest.get("session_id"))
        except Exception as e:
            return json.dumps({"error": f"Failed to read CO data: {e}"})

    if not co_data:
        return json.dumps({"error": "No capacity data found. Run CO agent first."})

    # Extract utilization from CO structured output
    util = co_data.get("utilization", [])
    rm_util = next((u for u in util if u.get("machine_type") == "Rolling Mill"), {})
    fl_util = next((u for u in util if u.get("machine_type") == "Finishing Line"), {})

    # CO structured output has total_surplus_hours. We need to split into
    # normal/overtime/weekend. The CO agent computes:
    #   normal_total = net_hrs_per_week * (window/5)
    #   ot_total = normal_total * 0.15
    #   wk_total = normal_total * 0.10
    #   normal_surplus = normal_total - committed
    # total_surplus = normal_surplus + ot_total + wk_total
    rm_total_surplus = float(rm_util.get("total_surplus_hours", 0))
    fl_total_surplus = float(fl_util.get("total_surplus_hours", 0))
    rm_pct = float(rm_util.get("normal_utilization_pct", 0))
    fl_pct = float(fl_util.get("normal_utilization_pct", 0))

    # Reverse-engineer the split: if pct < 100, normal_surplus > 0
    # normal_total = total_surplus / (1 - pct/100 + 0.15 + 0.10) approximately
    # Simpler: use the known equipment hours. Ohio RM: 74 net/week, FL: 76 net/week
    # window = 10 days = 2 weeks
    # But we don't have the raw equipment data here. Use the ratio approach:
    # total_surplus = normal_surplus + ot + weekend
    # ot = normal_total * 0.15, weekend = normal_total * 0.10
    # normal_surplus = normal_total * (1 - pct/100)
    # total_surplus = normal_total * (1 - pct/100 + 0.15 + 0.10)
    # So normal_total = total_surplus / (1.25 - pct/100)
    def split_surplus(total_surplus: float, pct: float) -> dict:
        denom = 1.25 - pct / 100.0
        if denom <= 0 or total_surplus <= 0:
            return {"normal_hrs": 0, "overtime_hrs": 0, "weekend_hrs": 0, "total_hrs": total_surplus}
        normal_total = total_surplus / denom
        normal_surplus = normal_total * (1 - pct / 100.0)
        ot_hrs = normal_total * 0.15
        wk_hrs = normal_total * 0.10
        return {
            "normal_hrs": round(max(normal_surplus, 0), 2),
            "overtime_hrs": round(ot_hrs, 2),
            "weekend_hrs": round(wk_hrs, 2),
            "total_hrs": round(normal_surplus + ot_hrs + wk_hrs, 2),
        }

    rm_shift = split_surplus(rm_total_surplus, rm_pct)
    fl_shift = split_surplus(fl_total_surplus, fl_pct)

    # Material surplus
    material_surplus = 0.0
    surplus_summary = co_data.get("surplus_summary") or co_data.get("total_surplus_summary")
    if surplus_summary and isinstance(surplus_summary, dict):
        material_surplus = float(surplus_summary.get("material_surplus_tons", 0))
    if material_surplus == 0:
        material_surplus = float(co_data.get("material_utilization_pct", 0))
        # If we only have pct, estimate tons (rough: 1000 total * (1-pct/100))
        if 0 < material_surplus < 100:
            material_surplus = round(1000 * (1 - material_surplus / 100), 0)

    # Workforce surplus
    workforce_surplus = 4  # default from seed data
    if surplus_summary and isinstance(surplus_summary, dict):
        workforce_surplus = int(surplus_summary.get("workforce_surplus_operators", 4))

    tracker = {
        "session_id": session_id,
        "last_updated": datetime.utcnow().isoformat() + "Z",
        "rolling_mill_remaining_hrs": rm_shift,
        "finishing_line_remaining_hrs": fl_shift,
        "material_remaining_tons": material_surplus,
        "workforce_remaining": workforce_surplus,
        "orders_processed": [],
        "orders_skipped": [],
        "orders_approved": [],
        "orders_rejected": [],
    }

    # Initialize the TrackerState singleton
    tracker_obj = RunningCapacityTracker.model_validate(tracker)
    TrackerState.initialize(tracker_obj)

    logger.info(
        "Tracker initialized from CO data",
        extra={
            "session_id": session_id,
            "rm_total": rm_shift["total_hrs"],
            "fl_total": fl_shift["total_hrs"],
            "material": material_surplus,
            "workforce": workforce_surplus,
        },
    )

    return json.dumps(tracker, default=str)


@tool
def evaluate_funnel_tool(
    order_json: str = "",
    equipment_json: str = "",
    materials_json: str = "",
    workforce_json: str = "",
    receiving_plant_orders_json: str = "",
    tracker_json: str = "",
    config_json: str = "",
) -> str:
    """Run the 4-layer constraint funnel on a single order.

    If arguments are empty, reads from staged data (call stage_erp_data first).
    Otherwise uses provided JSON strings.

    Args:
        order_json: JSON of the disrupted plant order dict (optional if staged).
        equipment_json: JSON array of equipment capabilities (optional if staged).
        materials_json: JSON of material inventory (optional if staged).
        workforce_json: JSON of workforce data (optional if staged).
        receiving_plant_orders_json: JSON array of receiving plant active orders (optional if staged).
        tracker_json: JSON of RunningCapacityTracker state.
        config_json: JSON of AgentConfig thresholds.
    """
    if order_json and equipment_json:
        order = json.loads(order_json)
        equipment = json.loads(equipment_json)
        materials = json.loads(materials_json)
        workforce = json.loads(workforce_json)
        receiving_plant_orders = json.loads(receiving_plant_orders_json) if receiving_plant_orders_json else []
    elif _staged_data:
        order = _staged_data["order"]
        equipment = _staged_data["equipment"]
        materials = _staged_data["materials"]
        workforce = _staged_data["workforce"]
        receiving_plant_orders = _staged_data["receiving_plant_orders"]
    else:
        return json.dumps({"error": "No data available. Call stage_erp_data first or provide JSON arguments."})

    # Guard: if order is a list (LLM passed all orders), take the first one
    if isinstance(order, list):
        if len(order) == 0:
            return json.dumps({"error": "Order list is empty. Provide a single order dict."})
        order = order[0]

    # Guard: validate order has required fields
    if not order.get("order_id"):
        logger.warning("evaluate_funnel_tool: order missing order_id, keys=%s", list(order.keys()))
        return json.dumps({"error": f"Order dict missing 'order_id'. Available keys: {list(order.keys())}. Ensure you pass a single order dict with order_id, product_family, quantity, etc."})

    # Always use the TrackerState singleton — ignore LLM-provided tracker_json
    # to prevent the LLM from passing incorrect zero-value trackers.
    try:
        state = TrackerState.get()
        tracker = state.tracker
        logger.info("Using existing TrackerState: RM=%.1f, FL=%.1f",
                     tracker.rolling_mill_remaining_hrs.total_hrs,
                     tracker.finishing_line_remaining_hrs.total_hrs)
    except AssertionError:
        # Auto-initialize from DynamoDB CO output
        logger.info("Auto-initializing tracker, session_id=%s", _current_session_id)
        init_result = initialize_tracker_from_capacity.__wrapped__(
            session_id=_current_session_id,
        )
        init_data = json.loads(init_result)
        if "error" in init_data:
            logger.error("Tracker auto-init failed: %s", init_data["error"])
            # Last resort: if DynamoDB read fails and LLM provided tracker, use it
            if tracker_json:
                logger.warning("Falling back to LLM-provided tracker_json")
                tracker = RunningCapacityTracker.model_validate(json.loads(tracker_json))
            else:
                return json.dumps({"error": f"tracker auto-init failed: {init_data['error']}"})
        else:
            try:
                state = TrackerState.get()
                tracker = state.tracker
                logger.info("Tracker auto-initialized: RM=%.1f, FL=%.1f",
                             tracker.rolling_mill_remaining_hrs.total_hrs,
                             tracker.finishing_line_remaining_hrs.total_hrs)
            except AssertionError:
                return json.dumps({"error": "tracker auto-init succeeded but state not set"})

    if not config_json:
        config = _get_config()
    else:
        config = AgentConfig.model_validate(json.loads(config_json))

    result = _evaluate_funnel(
        order, equipment, materials, workforce,
        receiving_plant_orders, tracker, config,
    )
    return json.dumps(result.model_dump(), default=str)


@tool
def simulate_cascade_tool(
    order_json: str,
    receiving_plant_orders_json: str,
    config_json: str,
) -> str:
    """Standalone cascade simulation for on-demand re-runs.

    Args:
        order_json: JSON of the disrupted plant order dict.
        receiving_plant_orders_json: JSON array of receiving plant active orders.
        config_json: JSON of AgentConfig thresholds.
    """
    order = json.loads(order_json)
    receiving_plant_orders = json.loads(receiving_plant_orders_json)
    config = AgentConfig.model_validate(json.loads(config_json))
    result = _simulate_cascade(order, receiving_plant_orders, config)
    return json.dumps(result.model_dump(), default=str)


@tool
def record_decision_tool(
    order_id: str,
    action: str,
    rm_hrs: float = 0.0,
    fl_hrs: float = 0.0,
    material_tons: float = 0.0,
    workforce: int = 0,
    recommendation_category: str = "",
) -> str:
    """Record a planner decision and update the running tracker.

    Args:
        order_id: Order ID (e.g. PO-2026-001).
        action: One of approve, reject, skip.
        rm_hrs: Rolling mill hours consumed (approve only).
        fl_hrs: Finishing line hours consumed (approve only).
        material_tons: Material tons consumed (approve only).
        workforce: Operator count consumed (approve only).
        recommendation_category: The funnel recommendation category.
    """
    state = TrackerState.get()
    if action == "approve":
        state.approve_order(
            order_id, rm_hrs, fl_hrs, material_tons,
            workforce, recommendation_category,
        )
    elif action == "reject":
        state.reject_order(order_id, recommendation_category)
    elif action == "skip":
        state.skip_order(order_id)
    else:
        return json.dumps({"error": f"Invalid action: {action}"})

    t = state.tracker
    return json.dumps({
        "order_id": order_id,
        "action": action,
        "tracker_summary": {
            "rm_remaining": t.rolling_mill_remaining_hrs.total_hrs,
            "fl_remaining": t.finishing_line_remaining_hrs.total_hrs,
            "material_remaining": t.material_remaining_tons,
            "workforce_remaining": t.workforce_remaining,
            "approved": len(t.orders_approved),
            "rejected": len(t.orders_rejected),
            "skipped": len(t.orders_skipped),
        },
    })


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
    initialize_tracker_from_capacity,
    evaluate_funnel_tool,
    simulate_cascade_tool,
    record_decision_tool,
]


_mcp_client_cached: MCPClient | None = None
_mcp_tools_cached: list | None = None
_oauth_token_expiry: float = 0


def _get_or_create_mcp_client(settings: AgentSettings) -> tuple[MCPClient, list]:
    """Return cached MCP client and tools, creating if needed.

    Caches the MCP connection and OAuth token across invocations to
    avoid the 2-3s overhead of token fetch + Gateway handshake per request.
    Token is refreshed 5 minutes before expiry.
    """
    global _mcp_client_cached, _mcp_tools_cached, _oauth_token_expiry
    import time as _time

    now = _time.time()
    if _mcp_client_cached is not None and _mcp_tools_cached is not None and now < _oauth_token_expiry - 300:
        return _mcp_client_cached, _mcp_tools_cached

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
    global _settings, _staged_data, _current_session_id
    _settings = settings or AgentSettings()
    _staged_data = {}
    _current_session_id = session_id

    configure_logging(_settings.log_level)
    logger.info(
        "Initializing Constraint Matching Agent",
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
                actor_id="constraint_matching",
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
        structured_output_model=ConstraintMatchingOutput,
        **({"session_manager": session_manager} if session_manager else {}),
    )

    logger.info("Constraint Matching Agent initialized")
    return agent


# -------------------------------------------------------------------
# Fail-closed invocation wrapper (Pattern 7)
# -------------------------------------------------------------------


def run_agent(agent: Agent, task: str, session_id: str) -> AgentResult:
    """Invoke the agent with fail-closed error handling.

    On any unhandled exception the wrapper returns an error result
    instead of propagating — constraint matching is all-or-nothing.

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
            error="Constraint Matching Agent encountered an error",
        )
