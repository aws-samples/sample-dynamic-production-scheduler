"""AgentCore-compatible Orchestrator Agent entry point.

Uses BedrockAgentCoreApp wrapper for deployment on
Bedrock AgentCore Managed Runtime. Creates an AgentCore
data plane client for sub-agent invocation.
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
import uuid  # noqa: E402
from concurrent.futures import ThreadPoolExecutor, as_completed  # noqa: E402
from dataclasses import dataclass  # noqa: E402
from typing import Any  # noqa: E402

from bedrock_agentcore.runtime import BedrockAgentCoreApp  # noqa: E402

logger = logging.getLogger("orchestrator_agent")

app = BedrockAgentCoreApp()


# -------------------------------------------------------------------
# AgentCore data plane client adapter
# -------------------------------------------------------------------

@dataclass
class AgentCoreInvokeResponse:
    """Simplified response from AgentCore invoke."""
    output_text: str


class AgentCoreClient:
    """Thin wrapper around boto3 bedrock-agentcore for sub-agent calls."""

    def __init__(self, region: str = "us-east-1"):
        import boto3
        from botocore.config import Config
        # Sub-agent invocations can take 2-3 minutes (impact assessment
        # scores 20 orders, updates each, then builds structured output).
        # Default boto3 read_timeout of 60s is too short.
        cfg = Config(
            read_timeout=900,
            connect_timeout=10,
            retries={"max_attempts": 0},
        )
        self._client = boto3.client(
            "bedrock-agentcore",
            region_name=region,
            config=cfg,
        )

    def invoke_agent(
        self, agent_arn: str, input_text: str, session_id: str
    ) -> AgentCoreInvokeResponse:
        """Invoke a sub-agent on AgentCore Runtime.

        Args:
            agent_arn: The full AgentCore runtime ARN.
            input_text: Prompt to send to the sub-agent.
            session_id: Session correlation ID.

        Returns:
            AgentCoreInvokeResponse with the agent's text output.
        """
        response = self._client.invoke_agent_runtime(
            agentRuntimeArn=agent_arn,
            payload=json.dumps({
                "prompt": input_text,
                "session_id": session_id,
            }),
        )

        # Handle streaming response (text/event-stream)
        content_type = response.get("contentType", "")
        if "text/event-stream" in content_type:
            # Collect all raw bytes first, then decode once to avoid
            # splitting multi-byte UTF-8 characters across chunk boundaries.
            raw_parts = []
            for line in response["response"].iter_lines(chunk_size=4096):
                if line:
                    raw_parts.append(line if isinstance(line, bytes) else line.encode("utf-8"))
            body = b"\n".join(raw_parts).decode("utf-8", errors="replace")
            # Strip SSE "data: " prefixes
            lines = body.split("\n")
            result_parts = []
            for ln in lines:
                stripped = ln.strip()
                if stripped.startswith("data: "):
                    stripped = stripped[6:]
                if stripped:
                    result_parts.append(stripped)
            body = "".join(result_parts)
        elif content_type == "application/json":
            chunks = []
            for chunk in response.get("response", []):
                chunks.append(chunk.decode("utf-8") if isinstance(chunk, bytes) else chunk)
            body = "".join(chunks)
        else:
            body = response.get("response", b"")
            if hasattr(body, "read"):
                body = body.read()
            if isinstance(body, bytes):
                body = body.decode("utf-8")

        try:
            parsed = json.loads(body)
            # Return the full JSON body so _invoke_sub_agent can extract
            # structured_output. If it's not JSON, return raw text.
            text = body
        except (json.JSONDecodeError, TypeError):
            text = body
        return AgentCoreInvokeResponse(output_text=str(text))


# Lazy-init to stay within 30s cold-start budget
_agent_factory_ready = False
_settings_cached = None
_ac_client_cached = None
_mcp_tools_cached = None

def _ensure_factory():
    """One-time initialization of settings, AgentCore client, and MCP tools.

    Caches the expensive MCP connection but does NOT cache the Agent
    instance — a fresh Agent is created per invocation to avoid
    Strands concurrency issues (REQ-B02).
    """
    global _agent_factory_ready, _settings_cached, _ac_client_cached, _mcp_tools_cached
    if _agent_factory_ready:
        return
    from orchestrator_agent.config import OrchestratorSettings
    from orchestrator_agent.logging_config import configure_logging

    _settings_cached = OrchestratorSettings()
    configure_logging(_settings_cached.log_level)
    _ac_client_cached = AgentCoreClient()
    _agent_factory_ready = True


def _create_agent_per_request(session_id: str = "", plant: str = ""):
    """Create a fresh Strands Agent for each invocation.

    Reuses cached settings and AgentCore client but creates a new
    Agent object to prevent ConcurrencyException (REQ-B02).
    """
    _ensure_factory()
    from orchestrator_agent.agent import create_agent
    return create_agent(_settings_cached, agentcore_client=_ac_client_cached, session_id=session_id, plant=plant)


def _invoke_round1_parallel(session_id: str, plant: str) -> dict[str, str]:
    """Invoke IA and CO sub-agents in parallel for Round 1.

    Uses ``concurrent.futures.ThreadPoolExecutor`` with two workers so
    both sub-agents run concurrently.  Each call goes through the
    existing ``_invoke_sub_agent`` helper which preserves retry logic,
    error recording, and structured-output extraction into the
    module-level accumulator.

    Returns:
        Dict mapping agent display name to its text result.
        On partial failure the failed agent's entry contains an error
        message while the successful agent's result is preserved.
    """
    from orchestrator_agent.agent import _invoke_sub_agent

    settings = _settings_cached

    def invoke_ia():
        return _invoke_sub_agent(
            agent_arn=settings.impact_assessment_agent_arn,
            prompt=f"Analyze and prioritize all active {plant} orders",
            name="Impact Assessment Agent",
        )

    def invoke_co():
        return _invoke_sub_agent(
            agent_arn=settings.capacity_optimization_agent_arn,
            prompt=f"Analyze {('Ohio' if plant == 'Florida' else 'Florida')} plant capacity for absorbing {plant} orders",
            name="Capacity & Optimization Agent",
        )

    results: dict[str, str] = {}
    with ThreadPoolExecutor(max_workers=2) as executor:
        futures = {
            executor.submit(invoke_ia): "Impact Assessment Agent",
            executor.submit(invoke_co): "Capacity & Optimization Agent",
        }
        for future in as_completed(futures):
            name = futures[future]
            try:
                results[name] = future.result()
            except Exception as e:
                results[name] = f"{name} failed: {str(e)}"

    return results


def _build_ui_payload(
    structured_outputs: dict[str, dict],
    phase: str,
    session_id: str = "",
    fresh_agent_keys: set[str] | None = None,
) -> dict:
    """Build UiPayload dict from sub-agent structured outputs.

    Pure function: takes accumulated structured outputs and the current
    workflow phase, returns a dict conforming to the UiPayload schema.
    No LLM involvement — deterministic Python dict construction.

    Args:
        structured_outputs: Dict keyed by agent name → structured_output dict.
        phase: Current workflow phase string from the frontend.
        session_id: Session ID for DynamoDB state access.
        fresh_agent_keys: Set of agent names whose outputs are fresh
            (produced in this invocation, not loaded from DynamoDB).
            Used to distinguish "CO output exists because it was persisted
            from Round 1" vs "CO just ran and produced new output".

    Returns:
        Dict with UiPayload fields, or empty dict when no outputs present.
    """
    if fresh_agent_keys is None:
        fresh_agent_keys = set()
    if not structured_outputs:
        return {}

    ui: dict = {}

    ia_output = structured_outputs.get("Impact Assessment Agent")
    co_output = structured_outputs.get("Capacity & Optimization Agent")
    cm_output = structured_outputs.get("Constraint Matching Agent")

    # --- Round 1 complete: both IA and CO outputs present AND phase is round1 ---
    if ia_output and co_output and phase in ("round1", "", "idle", "disruption_detected"):
        ui["phase"] = "round1_complete"

        # Orders from Impact Assessment
        orders = []
        for o in ia_output.get("scored_orders", []):
            orders.append({
                "orderId": o.get("order_id", ""),
                "product": o.get("product_family", ""),
                "customer": o.get("customer_name", ""),
                "customerTier": o.get("customer_tier", ""),
                "value": f"${o.get('order_value', 0):,.0f}",
                "dueDate": o.get("due_date", ""),
                "priority": o.get("priority", ""),
            })
        ui["orders"] = orders

        # Capacity from Capacity Optimization
        util = co_output.get("utilization", [])
        rm_pct = next(
            (u.get("normal_utilization_pct", 0) for u in util if u.get("machine_type") == "Rolling Mill"),
            0,
        )
        fl_pct = next(
            (u.get("normal_utilization_pct", 0) for u in util if u.get("machine_type") == "Finishing Line"),
            0,
        )
        rm_surplus = next(
            (u.get("total_surplus_hours", 0) for u in util if u.get("machine_type") == "Rolling Mill"),
            0,
        )
        fl_surplus = next(
            (u.get("total_surplus_hours", 0) for u in util if u.get("machine_type") == "Finishing Line"),
            0,
        )
        ui["capacity"] = {
            "rollingMill": rm_pct,
            "finishingLine": fl_pct,
            "rollingMillSurplusHrs": rm_surplus,
            "finishingLineSurplusHrs": fl_surplus,
            "rawMaterial": co_output.get("material_utilization_pct", 0),
            "workforce": co_output.get("workforce_utilization_pct", 0),
        }

        # Priorities from Impact Assessment
        ps = ia_output.get("priority_summary", {})
        ui["priorities"] = {
            "P1": ps.get("p1_count", 0),
            "P2": ps.get("p2_count", 0),
            "P3": ps.get("p3_count", 0),
            "P1Value": f"${ps.get('p1_total_value', 0):,.0f}",
            "P2Value": f"${ps.get('p2_total_value', 0):,.0f}",
            "P3Value": f"${ps.get('p3_total_value', 0):,.0f}",
        }

        ui["totalOrders"] = ps.get("total_orders", len(orders))
        ui["totalValue"] = f"${ia_output.get('total_value', 0):,.0f}"
        ui["bottleneck"] = co_output.get("bottleneck", "")

    # --- Partial Round 1: only CO output during round1 (IA failed) ---
    elif co_output and not ia_output and phase in ("round1", "", "idle"):
        ui["phase"] = "round1_complete"
        ui["orders"] = []  # IA failed — no scored orders

        # Capacity from CO
        util = co_output.get("utilization", [])
        rm_pct = next(
            (u.get("normal_utilization_pct", 0) for u in util if u.get("machine_type") == "Rolling Mill"),
            0,
        )
        fl_pct = next(
            (u.get("normal_utilization_pct", 0) for u in util if u.get("machine_type") == "Finishing Line"),
            0,
        )
        rm_surplus = next(
            (u.get("total_surplus_hours", 0) for u in util if u.get("machine_type") == "Rolling Mill"),
            0,
        )
        fl_surplus = next(
            (u.get("total_surplus_hours", 0) for u in util if u.get("machine_type") == "Finishing Line"),
            0,
        )
        ui["capacity"] = {
            "rollingMill": rm_pct,
            "finishingLine": fl_pct,
            "rollingMillSurplusHrs": rm_surplus,
            "finishingLineSurplusHrs": fl_surplus,
            "rawMaterial": co_output.get("material_utilization_pct", 0),
            "workforce": co_output.get("workforce_utilization_pct", 0),
        }
        ui["priorities"] = {"P1": 0, "P2": 0, "P3": 0, "P1Value": "$0", "P2Value": "$0", "P3Value": "$0"}
        ui["totalOrders"] = 0
        ui["totalValue"] = "$0"
        ui["bottleneck"] = co_output.get("bottleneck", "")

    # --- Delay optimization: CO output with delay candidates ---
    # Only match when explicitly in delay phase — NOT during round1
    # (during round1, CO output without IA means IA failed; show partial round1)
    elif phase in ("round2_delays", "delay_optimization"):
        # Use DynamoDB-backed sequential candidate access.
        # If CO just returned fresh candidates, they're already persisted
        # by save_structured_outputs in invoke(). Read the current candidate
        # from DynamoDB using the stored index.
        from orchestrator_agent.workflow_state import (
            get_next_delay_candidate,
            advance_delay_index,
        )

        # Advance the index when this is a decision response.
        # The LLM re-invokes CO on every delay decision, so CO is always
        # in fresh_agent_keys. Instead, we track whether delay_candidates
        # already existed before this invocation — if they did, this is
        # a decision response and we should advance.  The first time
        # (Round 1 → delay phase transition), delay_candidates were just
        # seeded so we don't advance.
        #
        # Simpler heuristic: advance if the delay_index is > 0 OR if
        # the previous candidate was already presented (index exists and
        # is not freshly seeded).  Since save_structured_outputs no longer
        # resets delay_index, we can just always advance here — the first
        # call into delay_optimization is the transition from round1 where
        # CO *does* produce fresh candidates and seeds index=0.  On that
        # first call the index is 0 and we present candidate[0].  On the
        # next call (user's decision), we advance to 1.
        from orchestrator_agent.workflow_state import load_state as _load_ws
        current_idx = _load_ws(session_id, "delay_index")
        # If index exists and is >= 0, this is not the first entry — advance
        if current_idx is not None and isinstance(current_idx, int) and current_idx >= 0:
            # Check if this is the very first delay_optimization call
            # by seeing if current_phase was already delay_optimization
            prev_phase = _load_ws(session_id, "current_phase")
            prev_phase_str = prev_phase.get("phase", "") if isinstance(prev_phase, dict) else ""
            if prev_phase_str in ("delay_optimization", "round2_delays"):
                # Not the first call — advance
                # Record decision on the current candidate before advancing
                prev_candidate = get_next_delay_candidate(session_id)
                if prev_candidate:
                    from orchestrator_agent.workflow_state import save_order_decision
                    save_order_decision(
                        session_id,
                        prev_candidate.get("order_id", ""),
                        "decided",
                        "delay_optimization",
                    )
                advance_delay_index(session_id)

        candidate = get_next_delay_candidate(session_id) if session_id else None
        if candidate:
            ui["phase"] = "delay_optimization"
            ui["approvalRequest"] = {
                "orderId": candidate.get("order_id", ""),
                "product": candidate.get("product_family", ""),
                "customer": candidate.get("customer_id", ""),
                "customerTier": candidate.get("customer_tier", ""),
                "value": f"${candidate.get('order_value', 0):,.0f}",
                "recommendation": candidate.get("trade_off_explanation", ""),
                "options": [
                    {"label": "APPROVE", "key": "approve", "hint": "Delay this order"},
                    {"label": "REJECT", "key": "reject", "hint": "Keep on schedule"},
                ],
            }
        else:
            # All candidates exhausted → transition to constraint funnel
            ui["phase"] = "constraint_funnel"

        # Include capacityImpact if present in the structured output
        if co_output and "capacityImpact" in co_output:
            ui["capacityImpact"] = co_output["capacityImpact"]

    # --- Constraint funnel: CM output with funnel results ---
    if cm_output:
        funnel_results = cm_output.get("funnel_results", [])
        if funnel_results:
            # If we haven't already set a phase from round1, set constraint_funnel
            if "phase" not in ui or phase in ("round2_funnel", "constraint_funnel"):
                ui["phase"] = "constraint_funnel"

            # Build approvalRequest from the first funnel result
            first_fr = funnel_results[0]
            ui["approvalRequest"] = {
                "orderId": first_fr.get("order_id", ""),
                "product": first_fr.get("product_family", ""),
                "customer": first_fr.get("customer_id", ""),
                "customerTier": first_fr.get("customer_tier", ""),
                "value": f"${first_fr.get('order_value', 0):,.0f}",
                "recommendation": first_fr.get("recommendation", ""),
                "reasoning": first_fr.get("reasoning", ""),
                "funnelResults": [
                    {
                        "layer": l.get("layer", 0),
                        "name": l.get("name", ""),
                        "passed": l.get("passed", False),
                        "detail": l.get("detail", ""),
                    }
                    for l in first_fr.get("layers", [])
                ],
                "options": [
                    {"label": "APPROVE", "key": "approve", "hint": "Reroute order"},
                    {"label": "REJECT", "key": "reject", "hint": "Keep at current plant"},
                    {"label": "SKIP", "key": "skip", "hint": "Decide later"},
                ],
            }

            # Include capacityImpact from CO if available
            if co_output and "capacityImpact" in co_output:
                ui["capacityImpact"] = co_output["capacityImpact"]

            # Build transferOrders from approved funnel results
            transfer_orders = []
            for fr in funnel_results:
                if fr.get("all_layers_passed", False):
                    transfer_orders.append({
                        "orderId": fr.get("order_id", ""),
                        "product": fr.get("product_family", ""),
                        "customer": fr.get("customer_id", ""),
                        "customerTier": fr.get("customer_tier", ""),
                        "value": f"${fr.get('order_value', 0):,.0f}",
                        "dueDate": fr.get("due_date", ""),
                        "priority": fr.get("priority", ""),
                        "recommendation": fr.get("recommendation", ""),
                        "reasoning": fr.get("reasoning", ""),
                        "funnelResults": [
                            {
                                "layer": l.get("layer", 0),
                                "name": l.get("name", ""),
                                "passed": l.get("passed", False),
                                "detail": l.get("detail", ""),
                            }
                            for l in fr.get("layers", [])
                        ],
                    })
            if transfer_orders:
                ui["transferOrders"] = transfer_orders

    # --- Summary phase ---
    if phase in ("summary", "complete") and not ui.get("phase"):
        ui["phase"] = "summary"
        ui["complete"] = True
        # Include transferOrders from CM if present
        if cm_output:
            funnel_results = cm_output.get("funnel_results", [])
            transfer_orders = []
            for fr in funnel_results:
                if fr.get("all_layers_passed", False):
                    transfer_orders.append({
                        "orderId": fr.get("order_id", ""),
                        "product": fr.get("product_family", ""),
                        "customer": fr.get("customer_id", ""),
                        "customerTier": fr.get("customer_tier", ""),
                        "value": f"${fr.get('order_value', 0):,.0f}",
                        "dueDate": fr.get("due_date", ""),
                        "priority": fr.get("priority", ""),
                        "recommendation": fr.get("recommendation", ""),
                        "reasoning": fr.get("reasoning", ""),
                        "funnelResults": [
                            {
                                "layer": l.get("layer", 0),
                                "name": l.get("name", ""),
                                "passed": l.get("passed", False),
                                "detail": l.get("detail", ""),
                            }
                            for l in fr.get("layers", [])
                        ],
                    })
            if transfer_orders:
                ui["transferOrders"] = transfer_orders

    return ui


@app.entrypoint
def invoke(payload, context):
    """Handle AgentCore invocation requests.

    Conversation continuity is handled by AgentCore Memory session manager
    with filter_restored_tool_context=True (strips toolUse/toolResult blocks
    on restore to prevent orphaned-block corruption).

    The UI payload is built deterministically from sub-agent structured
    outputs — no LLM involvement, no trailers, no fallback extraction.

    Args:
        payload: Dict with 'prompt' key containing the task.
        context: AgentCore runtime context (has session_id from runtimeSessionId).

    Returns:
        Dict with 'result', 'ui', and 'session_id' keys.
    """
    prompt = payload.get("prompt", "")
    plant = payload.get("plant", "")
    current_phase = payload.get("currentPhase", "")

    # Prefer runtimeSessionId from AgentCore context (set via header),
    # fall back to payload session_id, then generate a new one.
    session_id = (
        getattr(context, "session_id", None)
        or payload.get("session_id")
        or str(uuid.uuid4())
    )

    logger.info(
        "AgentCore invoke received",
        extra={"session_id": session_id, "prompt_length": len(prompt), "plant": plant},
    )

    from orchestrator_agent.agent import run_agent, _reset_structured_outputs, _get_structured_outputs

    _reset_structured_outputs()
    agent = _create_agent_per_request(session_id=session_id, plant=plant)

    # Detect Round 1: initial disruption report (intelligence gathering phase).
    # Round 1 happens when the user first reports a disruption — the phase will
    # be empty, "idle", "disruption_detected", or "round1" (set by frontend
    # startDisruption before the first message is sent).
    is_round1 = current_phase in ("", "idle", "disruption_detected", "round1")

    if is_round1 and plant:
        # Parallel sub-agent invocation for Round 1
        round1_results = _invoke_round1_parallel(session_id, plant)

        # Persist structured outputs immediately — before run_agent() which
        # can take minutes and trigger AgentCore retries that lose in-memory state.
        structured_after_parallel = _get_structured_outputs()
        if structured_after_parallel:
            from orchestrator_agent.workflow_state import save_structured_outputs
            save_structured_outputs(session_id, structured_after_parallel)
            logger.info(
                "Persisted Round 1 structured outputs to DynamoDB",
                extra={"agents": list(structured_after_parallel.keys()), "session_id": session_id},
            )

        # Build enriched prompt with sub-agent results so the LLM can
        # generate a natural-language summary for the Planner.
        sub_agent_context = "\n\n".join(
            f"--- {name} ---\n{text}" for name, text in round1_results.items()
        )
        effective_prompt = (
            f"[Frontend phase: round1_in_progress]\n"
            f"The following sub-agent analyses have been completed in parallel:\n\n"
            f"{sub_agent_context}\n\n"
            f"Original request: {prompt}\n\n"
            f"Summarize the findings for the Planner. The UI data has been handled automatically."
        )
    else:
        # Normal LLM-driven invocation for other phases
        effective_prompt = prompt
        if current_phase:
            effective_prompt = f"[Frontend phase: {current_phase}]\n{prompt}"

    result = run_agent(agent, effective_prompt, session_id)

    # Persist structured outputs to DynamoDB for cross-invocation access
    structured = _get_structured_outputs()
    if structured:
        from orchestrator_agent.workflow_state import save_structured_outputs
        save_structured_outputs(session_id, structured)

    # Merge in-memory outputs with persisted state from DynamoDB.
    # In-memory outputs take precedence (fresh from this invocation).
    from orchestrator_agent.workflow_state import load_all_structured_outputs
    persisted = load_all_structured_outputs(session_id)
    merged = {**persisted, **structured}

    # --- Auto-invoke Constraint Matching when transitioning to funnel ---
    # When delay candidates are exhausted, _build_ui_payload sets phase to
    # constraint_funnel but the CM agent hasn't been invoked yet. Detect
    # this gap and eagerly invoke CM so the frontend gets funnel results
    # in the same response instead of waiting for the next user message.
    if "Constraint Matching Agent" not in merged:
        # Build a preliminary UI payload to check if phase would be constraint_funnel
        preliminary_ui = _build_ui_payload(merged, current_phase, session_id, fresh_agent_keys=set(structured.keys()))
        if preliminary_ui.get("phase") == "constraint_funnel" and plant:
            logger.info(
                "Auto-invoking Constraint Matching Agent for funnel phase",
                extra={"session_id": session_id},
            )
            from orchestrator_agent.agent import _invoke_sub_agent
            receiving_plant = "Ohio" if plant == "Florida" else "Florida"
            _invoke_sub_agent(
                agent_arn=_settings_cached.constraint_matching_agent_arn,
                prompt=f"Run the 4-layer constraint funnel for all disrupted {plant} orders in priority order (P1 first). Receiving plant is {receiving_plant}.",
                name="Constraint Matching Agent",
            )
            # Re-collect structured outputs after CM invocation
            structured = _get_structured_outputs()
            if structured:
                save_structured_outputs(session_id, structured)
            persisted = load_all_structured_outputs(session_id)
            merged = {**persisted, **structured}

    logger.info(
        "Building UI payload",
        extra={
            "structured_output_agents": list(structured.keys()),
            "persisted_agents": list(persisted.keys()),
            "merged_agents": list(merged.keys()),
            "current_phase": current_phase,
        },
    )
    ui = _build_ui_payload(merged, current_phase, session_id, fresh_agent_keys=set(structured.keys()))
    logger.info(
        "UI payload built",
        extra={"ui_keys": list(ui.keys()), "ui_phase": ui.get("phase", "none")},
    )

    # Persist the resolved phase to DynamoDB so the frontend can poll it
    resolved_phase = ui.get("phase", current_phase)
    if resolved_phase and session_id:
        from orchestrator_agent.workflow_state import save_phase
        save_phase(session_id, resolved_phase)

    if result.success:
        return {
            "result": result.data,
            "ui": ui,
            "session_id": session_id,
        }
    else:
        return {
            "error": result.error,
            "session_id": session_id,
            "success": False,
        }


if __name__ == "__main__":
    app.run()
