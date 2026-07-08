"""Orchestrator Agent entry point.

Initializes Strands Agent with Claude 4.5 Haiku, registers sub-agent
tools (AgentCore invoke), MCP tools (Audit MCP via Gateway), and
session tools. Exposes the fail-closed invocation wrapper (Pattern 7).
"""

from __future__ import annotations

import json
import logging
import time
from typing import Any

from strands import Agent, tool
from strands.models.bedrock import BedrockModel
from strands.tools.mcp import MCPClient

from orchestrator_agent.config import OrchestratorSettings
from orchestrator_agent.logging_config import configure_logging
from orchestrator_agent.models.schemas import (
    AgentError,
    AgentResult,
    WorkflowPhase,
)
from orchestrator_agent.prompts.system_prompt import get_system_prompt
from orchestrator_agent.session import WorkflowSession, create_session

logger = logging.getLogger("orchestrator_agent")


# -------------------------------------------------------------------
# Structured output accumulator (Deterministic JSON Pipeline)
# -------------------------------------------------------------------

# Module-level dict keyed by agent name → structured_output dict.
# Reset at the start of each orchestrator invocation.
_structured_outputs: dict[str, dict] = {}

# Persistent delay candidates cache — survives across invocations within
# the same Lambda container. Populated when CO agent returns delay_candidates
# in Round 1 or delay optimization. The index tracks which candidate to
# present next in the UI.
_delay_candidates_cache: list[dict] = []
_delay_candidate_index: int = 0


def _reset_structured_outputs() -> None:
    """Reset the structured output accumulator for a new invocation."""
    global _structured_outputs
    _structured_outputs = {}


def _get_structured_outputs() -> dict[str, dict]:
    """Return all accumulated structured outputs from sub-agent responses."""
    return _structured_outputs


def _cache_delay_candidates(candidates: list[dict]) -> None:
    """Cache delay candidates from CO agent output."""
    global _delay_candidates_cache, _delay_candidate_index
    if candidates:
        _delay_candidates_cache = candidates
        _delay_candidate_index = 0


def _advance_delay_candidate() -> None:
    """Move to the next delay candidate after a decision."""
    global _delay_candidate_index
    _delay_candidate_index += 1


def _get_current_delay_candidate() -> dict | None:
    """Return the current delay candidate, or None if exhausted."""
    if _delay_candidate_index < len(_delay_candidates_cache):
        return _delay_candidates_cache[_delay_candidate_index]
    return None


def _get_delay_candidate_index() -> int:
    """Return the current delay candidate index."""
    return _delay_candidate_index


def _get_delay_candidates_cache() -> list[dict]:
    """Return the full delay candidates cache."""
    return _delay_candidates_cache


# -------------------------------------------------------------------
# Module-level state (populated by create_agent)
# -------------------------------------------------------------------

_settings: OrchestratorSettings | None = None
_session: WorkflowSession | None = None
_agentcore_client: Any = None  # AgentCore runtime client

# Per-session workflow state cache — survives across per-request Agent
# creation so that phase transitions are not lost between invocations.
_session_cache: dict[str, WorkflowSession] = {}
_MAX_SESSION_CACHE = 50  # Evict oldest sessions beyond this limit


def _get_settings() -> OrchestratorSettings:
    assert _settings is not None, "Agent not initialized"
    return _settings


def _get_session() -> WorkflowSession:
    assert _session is not None, "Session not initialized"
    return _session


# -------------------------------------------------------------------
# Sub-agent invocation helper (Pattern 2)
# -------------------------------------------------------------------

def _invoke_sub_agent(agent_arn: str, prompt: str, name: str) -> str:
    """Invoke a sub-agent via AgentCore API with retry.

    Returns the agent's text output on success, or an error message
    on permanent failure. When the response contains a ``structured_output``
    key, the parsed dict is stored in the module-level ``_structured_outputs``
    accumulator keyed by *name* so that the orchestrator's agentcore_server
    can build the UI payload deterministically.

    Logs errors and records them in session.
    """
    global _structured_outputs
    settings = _get_settings()
    session = _get_session()

    for attempt in range(1 + settings.retry_limit):
        try:
            start = time.time()
            response = _agentcore_client.invoke_agent(
                agent_arn=agent_arn,
                input_text=prompt,
                session_id=session.session_id,
            )
            duration_ms = int((time.time() - start) * 1000)
            logger.info(
                "Sub-agent completed",
                extra={
                    "agent": name,
                    "duration_ms": duration_ms,
                    "session_id": session.session_id,
                },
            )

            # --- Extract structured_output if present ---
            text = response.output_text
            try:
                parsed = json.loads(text)
                if isinstance(parsed, dict) and "structured_output" in parsed:
                    _structured_outputs[name] = parsed["structured_output"]
                    logger.info(
                        "Structured output extracted",
                        extra={"agent": name, "keys": list(parsed["structured_output"].keys())},
                    )
                    # Eagerly persist to DynamoDB so the frontend poller
                    # can pick up results before the orchestrator finishes.
                    try:
                        from orchestrator_agent.workflow_state import save_structured_outputs
                        save_structured_outputs(
                            session.session_id, {name: parsed["structured_output"]}
                        )
                        logger.info(
                            "Eagerly persisted structured output",
                            extra={"agent": name, "session_id": session.session_id},
                        )
                    except Exception:
                        logger.warning(
                            "Eager persist failed (will retry at end of invoke)",
                            extra={"agent": name},
                            exc_info=True,
                        )
                    # Use the text summary for LLM reasoning
                    text = parsed.get("result", text)
            except (json.JSONDecodeError, TypeError, AttributeError):
                # Response is not JSON — use raw text as-is
                pass

            return f"[SUCCESS — {name} completed in {duration_ms}ms]\n{text}"
        except Exception as e:
            if attempt < settings.retry_limit:
                logger.warning(
                    "Sub-agent failed, retrying after %ds delay",
                    extra={"agent": name, "attempt": attempt,
                           "delay_seconds": settings.retry_delay_seconds,
                           "error": str(e)},
                    exc_info=True,
                )
                time.sleep(settings.retry_delay_seconds)
                continue
            logger.error(
                "Sub-agent failed after retry",
                extra={"agent": name, "error": str(e)},
            )
            session.record_error(AgentError(
                agent_id=agent_arn,
                error_type="exception",
                message=str(e),
                retried=True,
                retry_succeeded=False,
            ))
            return f"{name} is unavailable: {str(e)}"


# -------------------------------------------------------------------
# Sub-agent tools — registered with Strands @tool decorator
# -------------------------------------------------------------------

@tool
def invoke_impact_assessment(prompt: str) -> str:
    """Invoke Impact Assessment Agent via AgentCore managed runtime.

    Prioritizes affected production orders by urgency, customer tier,
    order value, and machine complexity. Use during Round 1.

    Args:
        prompt: Natural language instruction for the Impact Assessment Agent.
    """
    settings = _get_settings()
    return _invoke_sub_agent(
        agent_arn=settings.impact_assessment_agent_arn,
        prompt=prompt,
        name="Impact Assessment Agent",
    )


@tool
def invoke_capacity_optimization(prompt: str) -> str:
    """Invoke Capacity & Optimization Agent via AgentCore managed runtime.

    Analyzes receiving plant capacity across 5 dimensions and manages
    delay candidates. Use during Round 1 and Round 2 delay phase.

    Args:
        prompt: Natural language instruction for the Capacity Agent.
    """
    settings = _get_settings()
    return _invoke_sub_agent(
        agent_arn=settings.capacity_optimization_agent_arn,
        prompt=prompt,
        name="Capacity & Optimization Agent",
    )


@tool
def invoke_constraint_matching(prompt: str) -> str:
    """Invoke Constraint Matching Agent via AgentCore managed runtime.

    Runs the 4-layer constraint funnel for order rerouting decisions.
    Use during Round 2 funnel phase.

    Args:
        prompt: Natural language instruction for the Constraint Agent.
    """
    settings = _get_settings()
    result = _invoke_sub_agent(
        agent_arn=settings.constraint_matching_agent_arn,
        prompt=prompt,
        name="Constraint Matching Agent",
    )
    # Truncate very long responses to prevent orchestrator context overflow.
    # The constraint matching agent can return 10K+ chars for 20 orders.
    max_len = 6000
    if len(result) > max_len:
        truncated = result[:max_len]
        result = f"{truncated}\n\n[TRUNCATED — Full response was {len(result)} chars. Present the orders shown above to the Planner for approval.]"
    return result


# -------------------------------------------------------------------
# Session tools — registered with Strands @tool decorator
# -------------------------------------------------------------------

@tool
def get_session_state() -> str:
    """Return the current workflow session state as JSON text.

    Provides the LLM with programmatic session context including
    current phase, decisions made, and error log.
    """
    session = _get_session()
    return json.dumps(session.to_dict(), default=str)


@tool
def update_session_phase(new_phase: str) -> str:
    """Transition the workflow session to a new phase.

    Valid phases: idle, disruption_detected, round1_in_progress,
    round1_complete, round2_delays, round2_funnel, what_if,
    summary, complete.

    Args:
        new_phase: The target workflow phase name.
    """
    session = _get_session()
    try:
        phase = WorkflowPhase(new_phase)
        session.transition(phase)
        return f"Phase updated to {new_phase}"
    except ValueError as e:
        return f"Invalid phase transition: {str(e)}"


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

_mcp_client_cached: MCPClient | None = None
_mcp_tools_cached: list | None = None
_oauth_token_expiry: float = 0


def _get_or_create_mcp_client_cached(settings: OrchestratorSettings) -> tuple[MCPClient, list]:
    """Return cached MCP client and tools, creating if needed.

    Caches the MCP connection and OAuth token across invocations to
    avoid the 2-3s overhead of token fetch + Gateway handshake per request.
    Token is refreshed 5 minutes before expiry.
    """
    global _mcp_client_cached, _mcp_tools_cached, _oauth_token_expiry

    now = time.time()
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
        [settings.erp_data_scope, settings.audit_scope],
    )
    _oauth_token_expiry = now + 3600  # 1 hour
    logger.info("MCP client connected, loaded %d tools", len(_mcp_tools_cached))
    return _mcp_client_cached, _mcp_tools_cached


PYTHON_TOOLS = [
    invoke_impact_assessment,
    invoke_capacity_optimization,
    invoke_constraint_matching,
    get_session_state,
    update_session_phase,
]


def create_agent(
    settings: OrchestratorSettings | None = None,
    agentcore_client: Any = None,
    session_id: str = "",
    plant: str = "",
) -> Agent:
    """Initialize and return a configured Strands Agent.

    Args:
        settings: Optional OrchestratorSettings. Loaded from env if None.
        agentcore_client: AgentCore runtime client for sub-agent calls.
        session_id: Session ID for AgentCore Memory persistence.

    Returns:
        Configured Agent instance with MCP + Python tools.
    """
    global _settings, _session, _agentcore_client
    _settings = settings or OrchestratorSettings()
    # Reuse existing session for this session_id if one exists,
    # otherwise create a fresh one and cache it.
    if session_id and session_id in _session_cache:
        _session = _session_cache[session_id]
        logger.info(
            "Reusing cached session",
            extra={"session_id": session_id, "phase": _session.current_phase.value},
        )
    else:
        _session = create_session()
        if session_id:
            _session.session_id = session_id
            _session_cache[session_id] = _session
            # Evict oldest sessions if cache exceeds limit
            if len(_session_cache) > _MAX_SESSION_CACHE:
                oldest_key = next(iter(_session_cache))
                del _session_cache[oldest_key]
            logger.info(
                "Created new session",
                extra={"session_id": session_id},
            )
    _agentcore_client = agentcore_client

    configure_logging(_settings.log_level)
    logger.info(
        "Initializing Orchestrator Agent",
        extra={"model": _settings.bedrock_model_id},
    )

    model = BedrockModel(
        model_id=_settings.bedrock_model_id,
        max_tokens=16384,
        temperature=0,
    )

    erp_mcp_client, all_tools = _get_or_create_mcp_client_cached(_settings)

    # AgentCore Memory session manager — re-enabled with tool block filtering.
    # filter_restored_tool_context=True strips toolUse/toolResult blocks
    # when restoring messages from Memory, preventing the orphaned-block
    # corruption that occurs when AgentCore retries long-running invocations.
    session_manager = None
    if _settings.agentcore_memory_id:
        try:
            from bedrock_agentcore.memory.integrations.strands.config import (
                AgentCoreMemoryConfig,
            )
            from bedrock_agentcore.memory.integrations.strands.session_manager import (
                AgentCoreMemorySessionManager,
            )

            memory_config = AgentCoreMemoryConfig(
                memory_id=_settings.agentcore_memory_id,
                session_id=session_id or "default",
                actor_id=f"orchestrator_{session_id or 'default'}",
                filter_restored_tool_context=True,
            )
            session_manager = AgentCoreMemorySessionManager(
                agentcore_memory_config=memory_config,
                region_name="us-east-1",
            )
            logger.info(
                "AgentCore Memory enabled with tool block filtering",
                extra={"memory_id": _settings.agentcore_memory_id, "session_id": session_id},
            )
        except Exception:
            logger.warning(
                "Failed to initialize AgentCore Memory — continuing without it",
                extra={"memory_id": _settings.agentcore_memory_id},
                exc_info=True,
            )
            session_manager = None

    from strands.tools.executors.concurrent import ConcurrentToolExecutor

    agent = Agent(
        model=model,
        system_prompt=get_system_prompt(plant=plant),
        tools=all_tools + PYTHON_TOOLS,
        tool_executor=ConcurrentToolExecutor(),
        session_manager=session_manager,
    )

    logger.info("Orchestrator Agent initialized")
    return agent


# -------------------------------------------------------------------
# Fail-closed invocation wrapper (Pattern 7)
# -------------------------------------------------------------------

def run_agent(agent: Agent, task: str, session_id: str) -> AgentResult:
    """Invoke the agent with fail-closed error handling.

    On any unhandled exception the wrapper returns an error result
    instead of propagating.

    Args:
        agent: Configured Strands Agent instance.
        task: Natural language task from the Planner.
        session_id: Correlation ID for logging and audit.

    Returns:
        AgentResult with success/failure and data or error message.
    """
    try:
        logger.info(
            "Orchestrator invoked",
            extra={"session_id": session_id, "task_length": len(task)},
        )
        result = agent(task)
        logger.info(
            "Orchestrator completed",
            extra={"session_id": session_id},
        )
        return AgentResult(success=True, data=str(result))
    except KeyboardInterrupt:
        logger.warning(
            "Orchestrator interrupted",
            extra={"session_id": session_id},
        )
        return AgentResult(
            success=False,
            error="Orchestrator Agent was interrupted",
        )
    except Exception:
        logger.error(
            "Orchestrator failed — returning error result",
            extra={"session_id": session_id},
            exc_info=True,
        )
        return AgentResult(
            success=False,
            error="Orchestrator Agent encountered an error",
        )
