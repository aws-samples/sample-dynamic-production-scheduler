"""Capacity & Optimization Agent entry point.

Initializes Strands Agent with Claude 4.5 Haiku, registers MCP tools
(via AgentCore Gateway) and Python tools (capacity engine), and exposes
the fail-closed invocation wrapper (Pattern 7).
"""

from __future__ import annotations

import json
import logging
from copy import deepcopy
from dataclasses import dataclass
from typing import Any

from strands import Agent, tool
from strands.models.bedrock import BedrockModel
from strands.tools.mcp import MCPClient

from capacity_optimization_agent.capacity import (
    CapacityState,
    build_delay_result,
    build_shared_snapshot,
    build_surplus_summary,
    check_utilization_warnings,
    compute_machine_utilization,
    enrich_orders,
    filter_delay_candidates as _filter_delay_candidates,
    identify_bottleneck,
)
from capacity_optimization_agent.config import AgentSettings
from capacity_optimization_agent.logging_config import configure_logging
from capacity_optimization_agent.models.schemas import (
    CapacityOptimizationOutput,
    CapacitySnapshot,
    DelayDecision,
    EquipmentCapability,
    WorkforceAvailability,
    MaterialSurplus,
    PlannerConstraint,
)
from capacity_optimization_agent.prompts.system_prompt import (
    get_full_system_prompt,
)

logger = logging.getLogger("capacity_optimization_agent")


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
# Module-level state (populated by create_agent)
# -------------------------------------------------------------------

_settings: AgentSettings | None = None
_capacity_state: CapacityState | None = None
_staged_data: dict[str, Any] = {}


def _get_settings() -> AgentSettings:
    assert _settings is not None, "Agent not initialized"
    return _settings


# -------------------------------------------------------------------
# Python tools — registered with Strands @tool decorator
# -------------------------------------------------------------------

@tool
def stage_erp_data(
    equipment_json: str,
    orders_json: str,
    customers_json: str,
    workforce_json: str,
    materials_json: str,
) -> str:
    """Stage fetched ERP data for subsequent capacity tools.

    Call this ONCE after fetching all data via MCP tools.
    Subsequent tools (compute_capacity_snapshot) will read from staged data
    automatically — no need to pass large JSON strings again.

    Args:
        equipment_json: JSON from get_machine_capacity MCP calls.
        orders_json: JSON from get_orders MCP call.
        customers_json: JSON from get_customers MCP call.
        workforce_json: JSON from get_workforce MCP call.
        materials_json: JSON from get_materials MCP call.
    """
    global _staged_data
    _staged_data = {
        "equipment": json.loads(equipment_json),
        "orders": json.loads(orders_json),
        "customers": json.loads(customers_json),
        "workforce": json.loads(workforce_json),
        "materials": json.loads(materials_json),
    }
    return json.dumps({
        "status": "staged",
        "equipment_count": len(_staged_data["equipment"]) if isinstance(_staged_data["equipment"], list) else 1,
        "orders_count": len(_staged_data["orders"]) if isinstance(_staged_data["orders"], list) else 0,
        "customers_count": len(_staged_data["customers"]) if isinstance(_staged_data["customers"], list) else len(_staged_data["customers"]),
        "workforce": "available" if _staged_data["workforce"] else "none",
        "materials": "available" if _staged_data["materials"] else "none",
    })


@tool
def compute_capacity_snapshot(
    equipment_json: str = "",
    orders_json: str = "",
    customers_json: str = "",
    workforce_json: str = "",
    materials_json: str = "",
) -> str:
    """Run full 5-dimension capacity analysis.

    Computes equipment capability, tiered machine utilization, workforce,
    materials, order load with slack, bottleneck, and surplus summary.
    Caches the snapshot for subsequent delay/constraint operations.

    If arguments are empty, reads from staged data (call stage_erp_data first).
    Otherwise uses provided JSON strings.

    Args:
        equipment_json: JSON from get_machine_capacity MCP calls (optional if staged).
        orders_json: JSON from get_orders MCP call (optional if staged).
        customers_json: JSON from get_customers MCP call (optional if staged).
        workforce_json: JSON from get_workforce MCP call (optional if staged).
        materials_json: JSON from get_materials MCP call (optional if staged).
    """
    global _capacity_state
    cfg = _get_settings().get_capacity_config()

    if equipment_json and orders_json:
        equipment_raw = json.loads(equipment_json)
        orders_raw = json.loads(orders_json)
        customers_raw = json.loads(customers_json) if customers_json else {}
        workforce_raw = json.loads(workforce_json) if workforce_json else {}
        materials_raw = json.loads(materials_json) if materials_json else []
    elif _staged_data:
        equipment_raw = _staged_data["equipment"]
        orders_raw = _staged_data["orders"]
        customers_raw = _staged_data["customers"]
        workforce_raw = _staged_data["workforce"]
        materials_raw = _staged_data["materials"]
    else:
        return json.dumps({"error": "No data available. Call stage_erp_data first or provide JSON arguments."})

    # Normalize customers
    if isinstance(customers_raw, list):
        customers = {c["customer_id"]: c for c in customers_raw}
    else:
        customers = customers_raw

    # Parse equipment capabilities
    if isinstance(equipment_raw, dict):
        equipment_raw = [equipment_raw]
    equipment: list[EquipmentCapability] = []
    for eq in equipment_raw:
        total_hrs = float(eq.get("total_hours_per_week", 0))
        downtime_hrs = float(eq.get("planned_downtime_hrs_week", 0))
        # net_available is not in raw DynamoDB data — compute it
        net_hrs = eq.get("net_available_hours_per_week") or (total_hrs - downtime_hrs)
        equipment.append(EquipmentCapability(
            machine_type=eq["machine_type"],
            total_hours_per_week=total_hrs,
            planned_downtime_hrs_week=downtime_hrs,
            net_available_hours_per_week=float(net_hrs),
            product_families_supported=eq.get("product_families_supported", eq.get("product_families", [])),
            gauge_range_min=eq.get("gauge_range_min"),
            gauge_range_max=eq.get("gauge_range_max"),
            setup_time_by_family=eq.get("setup_time_by_family") or {},
        ))

    # Compute tiered utilization per machine
    utilization_list = []
    window = cfg.rerouting_window_days

    # Filter orders to those due within the rerouting window so committed
    # hours match the capacity window denominator.
    from datetime import datetime as _dt, timedelta as _td
    try:
        today = _dt.utcnow().date()
    except Exception:
        today = _dt(2026, 4, 7).date()
    window_end = today + _td(days=window)

    window_orders = []
    for o in orders_raw:
        due = o.get("due_date", "")
        if due:
            try:
                due_date = _dt.strptime(due[:10], "%Y-%m-%d").date()
                if due_date <= window_end:
                    window_orders.append(o)
            except (ValueError, TypeError):
                window_orders.append(o)  # include if date unparseable
        else:
            window_orders.append(o)

    for eq in equipment:
        normal_total = eq.net_available_hours_per_week * (window / 5.0)
        committed = sum(
            float(o.get("rolling_mill_hours", 0.0))
            if eq.machine_type == "Rolling Mill"
            else float(o.get("finishing_line_hours", 0.0))
            for o in window_orders
        )
        ot_total = normal_total * 0.15  # 15% overtime availability
        wk_total = normal_total * 0.10  # 10% weekend availability
        utilization_list.append(compute_machine_utilization(
            eq.machine_type, normal_total, committed, ot_total, wk_total,
        ))

    # Parse workforce
    workforce = None
    if workforce_raw:
        workforce = WorkforceAvailability(
            total_operators=workforce_raw.get("total_operators", 0),
            currently_allocated=workforce_raw.get("currently_allocated", 0),
            available_surplus=workforce_raw.get("available_surplus", 0),
            overtime_hrs_per_shift=workforce_raw.get("overtime_hrs_per_shift", 0.0),
            weekend_hrs_per_shift=workforce_raw.get("weekend_hrs_per_shift", 0.0),
            operators_per_rolling_mill=workforce_raw.get("operators_per_rolling_mill", 2),
            operators_per_finishing_line=workforce_raw.get("operators_per_finishing_line", 1),
        )

    # Parse materials — handle both raw list and {"materials": [...]} wrapper
    if isinstance(materials_raw, dict):
        materials_list = materials_raw.get("materials", [])
    elif isinstance(materials_raw, list):
        materials_list = materials_raw
    else:
        materials_list = []
    materials = [
        MaterialSurplus(
            material_type=m.get("material_type", ""),
            current_inventory_tons=m.get("current_inventory_tons", 0.0),
            committed_to_orders_tons=m.get("committed_to_orders_tons", 0.0),
            available_surplus_tons=m.get("available_surplus_tons", 0.0),
        )
        for m in materials_list
    ]

    # Enrich orders with slack
    enriched_orders = enrich_orders(orders_raw, customers, equipment)

    # Florida demand estimate (from orders or default)
    florida_demand: dict[str, float] = {"Rolling Mill": 100.0, "Finishing Line": 60.0}

    # Bottleneck and surplus
    bottleneck = identify_bottleneck(utilization_list, florida_demand)
    surplus_summary = build_surplus_summary(utilization_list, materials, workforce)

    # Warnings
    warnings = check_utilization_warnings(
        utilization_list, cfg.utilization_warning_pct,
    )

    # Build snapshot
    from datetime import datetime
    snapshot = CapacitySnapshot(
        session_id="",
        analyzed_at=datetime.utcnow().isoformat() + "Z",
        rerouting_window_days=window,
        equipment=equipment,
        utilization=utilization_list,
        workforce=workforce,
        materials=materials,
        existing_load=enriched_orders,
        bottleneck=bottleneck,
        total_surplus_summary=surplus_summary,
        active_constraints=[],
    )

    # Cache for recalculations (Pattern 8)
    _capacity_state = CapacityState(snapshot)

    result = snapshot.model_dump()
    # Flatten normal_utilization_pct into each utilization entry so the
    # structured output model can map it directly without LLM interpretation.
    for u in result.get("utilization", []):
        normal = u.get("normal", {})
        u["normal_utilization_pct"] = normal.get("utilization_pct", 0.0)
    # Add top-level utilization percentages for workforce and materials
    # so the structured output model can map them directly.
    if workforce:
        result["workforce_utilization_pct"] = round(
            (workforce.currently_allocated / workforce.total_operators * 100.0)
            if workforce.total_operators > 0 else 0.0, 1
        )
    else:
        result["workforce_utilization_pct"] = 0.0
    total_material = sum(m.current_inventory_tons for m in materials)
    committed_material = sum(m.committed_to_orders_tons for m in materials)
    result["material_utilization_pct"] = round(
        (committed_material / total_material * 100.0) if total_material > 0 else 0.0, 1
    )
    if warnings:
        result["utilization_warnings"] = warnings

    # Automatically filter delay candidates so they're included in the
    # structured output without requiring a separate tool call.
    from capacity_optimization_agent.capacity import filter_delay_candidates as _filter_delay_candidates
    all_enriched = enrich_orders(orders_raw, customers, equipment)
    from capacity_optimization_agent.models.schemas import OhioOrderLoad
    enriched_models = []
    for o in all_enriched:
        try:
            enriched_models.append(OhioOrderLoad.model_validate(o if isinstance(o, dict) else o.model_dump()))
        except Exception:
            pass
    delay_candidates = _filter_delay_candidates(
        enriched_models, cfg.delay_threshold_days, workforce, bottleneck.machine_type if bottleneck else "Rolling Mill",
    )
    result["delay_candidates"] = [c.model_dump() for c in delay_candidates]

    return json.dumps(result, default=str)


def _build_capacity_impact(
    state: CapacityState,
    sender_plant: str = "Florida",
    receiver_plant: str = "Ohio",
) -> dict:
    """Build capacityImpact dict from CapacityState snapshot.

    Computes utilization percentages from the cached snapshot's
    MachineUtilization objects. Sender plant is at 0% (disrupted).
    """
    snapshot = state.snapshot

    rm_util = fl_util = 0.0
    for mu in snapshot.utilization:
        if mu.machine_type == "Rolling Mill":
            rm_util = mu.normal.utilization_pct
        elif mu.machine_type == "Finishing Line":
            fl_util = mu.normal.utilization_pct

    overall = (rm_util + fl_util) / 2 if (rm_util + fl_util) > 0 else 0

    return {
        "senderPlant": {
            "name": sender_plant,
            "rollingMill": {"current": 0, "projected": 0},
            "finishingLine": {"current": 0, "projected": 0},
            "overall": {"current": 0, "projected": 0},
        },
        "receiverPlant": {
            "name": receiver_plant,
            "rollingMill": {"current": round(rm_util, 1), "projected": round(rm_util, 1)},
            "finishingLine": {"current": round(fl_util, 1), "projected": round(fl_util, 1)},
            "overall": {"current": round(overall, 1), "projected": round(overall, 1)},
        },
    }


@tool
def filter_delay_candidates_tool(
    orders_json: str,
    workforce_json: str,
    bottleneck_machine: str,
) -> str:
    """Identify P3 Ohio orders eligible for delay.

    Filters by priority, slack threshold, and penalty clause.
    Sorts by freed bottleneck capacity descending.

    Args:
        orders_json: JSON of enriched Ohio orders.
        workforce_json: JSON of workforce data.
        bottleneck_machine: Current bottleneck machine type.
    """
    cfg = _get_settings().get_capacity_config()
    orders_raw = json.loads(orders_json)
    workforce_raw = json.loads(workforce_json)

    from capacity_optimization_agent.models.schemas import OhioOrderLoad
    orders = [OhioOrderLoad.model_validate(o) for o in orders_raw]

    workforce = None
    if workforce_raw:
        workforce = WorkforceAvailability.model_validate(workforce_raw)

    candidates = _filter_delay_candidates(
        orders, cfg.delay_threshold_days, workforce, bottleneck_machine,
    )
    return json.dumps([c.model_dump() for c in candidates], default=str)


@tool
def process_delay_decision(
    order_id: str,
    action: str,
    florida_demand_json: str,
) -> str:
    """Apply a single delay approval/rejection with immediate recalculation.

    Uses cached snapshot (Pattern 8) — no MCP re-fetch needed.

    Args:
        order_id: The Ohio order ID to approve or reject.
        action: "approve" or "reject".
        florida_demand_json: JSON dict of machine_type -> demand hours.
    """
    global _capacity_state
    assert _capacity_state is not None, "No capacity snapshot cached"

    florida_demand = json.loads(florida_demand_json)
    before_summary = deepcopy(_capacity_state.snapshot.total_surplus_summary)
    before_bottleneck = deepcopy(_capacity_state.snapshot.bottleneck)

    if action == "approve":
        # Find order in cached snapshot
        order = None
        for o in _capacity_state.snapshot.existing_load:
            if o.order_id == order_id:
                order = o
                break
        if order is None:
            return json.dumps({"error": f"Order {order_id} not found"})

        _capacity_state.apply_delay(
            order_id=order_id,
            freed_rm=order.rolling_mill_hours,
            freed_fl=order.finishing_line_hours,
            freed_material=order.raw_material_tons,
            freed_operators=2,
            florida_demand=florida_demand,
        )

    after = _capacity_state.snapshot
    return json.dumps({
        "order_id": order_id,
        "action": action,
        "surplus_after": after.total_surplus_summary.model_dump(),
        "bottleneck_after": after.bottleneck.model_dump(),
        "capacityImpact": _build_capacity_impact(_capacity_state),
    }, default=str)


@tool
def apply_constraint_tool(
    constraint_text: str,
    constraint_type: str,
    florida_demand_json: str,
) -> str:
    """Apply a planner constraint with immediate recalculation.

    Uses cached snapshot (Pattern 8) — no MCP re-fetch needed.

    Args:
        constraint_text: Natural language constraint (e.g. "No weekend shifts").
        constraint_type: One of shift_restriction, capacity_limit, other.
        florida_demand_json: JSON dict of machine_type -> demand hours.
    """
    assert _capacity_state is not None, "No capacity snapshot cached"

    florida_demand = json.loads(florida_demand_json)
    constraint = PlannerConstraint(
        constraint_text=constraint_text,
        constraint_type=constraint_type,
    )
    impact = _capacity_state.apply_constraint(constraint, florida_demand)
    result = impact.model_dump()
    result["capacityImpact"] = _build_capacity_impact(_capacity_state)
    return json.dumps(result, default=str)


@tool
def check_utilization_warnings_tool(
    utilization_json: str,
    warning_pct: float,
) -> str:
    """Flag machines above utilization threshold.

    Args:
        utilization_json: JSON array of MachineUtilization objects.
        warning_pct: Warning threshold as decimal (e.g. 0.90).
    """
    from capacity_optimization_agent.models.schemas import MachineUtilization as MU
    raw = json.loads(utilization_json)
    util_list = [MU.model_validate(u) for u in raw]
    warnings = check_utilization_warnings(util_list, warning_pct)
    return json.dumps(warnings)


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
    compute_capacity_snapshot,
    filter_delay_candidates_tool,
    process_delay_decision,
    apply_constraint_tool,
    check_utilization_warnings_tool,
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
    global _settings, _staged_data
    _settings = settings or AgentSettings()
    _staged_data = {}

    configure_logging(_settings.log_level)
    logger.info(
        "Initializing Capacity & Optimization Agent",
        extra={"model": _settings.bedrock_model_id},
    )

    model = BedrockModel(
        model_id=_settings.bedrock_model_id,
        max_tokens=8192,
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
                actor_id="capacity_optimization",
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
        structured_output_model=CapacityOptimizationOutput,
        **({"session_manager": session_manager} if session_manager else {}),
    )

    logger.info("Capacity & Optimization Agent initialized")
    return agent


# -------------------------------------------------------------------
# Fail-closed invocation wrapper (Pattern 7)
# -------------------------------------------------------------------

def run_agent(agent: Agent, task: str, session_id: str) -> AgentResult:
    """Invoke the agent with fail-closed error handling.

    On any unhandled exception the wrapper returns an error result
    instead of propagating — capacity analysis is all-or-nothing.

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
            error="Capacity & Optimization Agent encountered an error",
        )
