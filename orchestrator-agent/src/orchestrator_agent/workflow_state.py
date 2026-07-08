"""Workflow state persistence via DynamoDB.

Stores and retrieves structured outputs from sub-agents so they
survive across Lambda cold starts. Keyed by session_id + state_key.

State keys:
  - "round1_ia": Impact Assessment structured output
  - "round1_co": Capacity Optimization structured output
  - "delay_candidates": List of delay candidates from CO
  - "delay_index": Current delay candidate index (int)
  - "funnel_results": Constraint Matching funnel results
"""

from __future__ import annotations

import json
import logging
import time
from decimal import Decimal

import boto3

logger = logging.getLogger("orchestrator_agent")

TABLE_NAME = "disruptionai-workflow-state"
TTL_HOURS = 24

_table = None


def _get_table():
    global _table
    if _table is None:
        _table = boto3.resource("dynamodb", region_name="us-east-1").Table(TABLE_NAME)
    return _table


def _to_decimal(obj):
    """Convert floats to Decimal for DynamoDB."""
    if isinstance(obj, float):
        return Decimal(str(obj))
    if isinstance(obj, dict):
        return {k: _to_decimal(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_to_decimal(i) for i in obj]
    return obj


def _from_decimal(obj):
    """Convert Decimals back to float/int."""
    if isinstance(obj, Decimal):
        return float(obj) if obj % 1 else int(obj)
    if isinstance(obj, dict):
        return {k: _from_decimal(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_from_decimal(i) for i in obj]
    return obj


def save_state(session_id: str, key: str, data: dict | list | int) -> None:
    """Write a workflow state entry to DynamoDB."""
    try:
        ttl = int(time.time()) + TTL_HOURS * 3600
        item = {
            "session_id": session_id,
            "state_key": key,
            "data": _to_decimal(data) if isinstance(data, (dict, list)) else data,
            "ttl": ttl,
        }
        _get_table().put_item(Item=item)
        logger.info("Workflow state saved", extra={"session_id": session_id, "key": key})
    except Exception:
        logger.warning("Failed to save workflow state", extra={"key": key}, exc_info=True)


def load_state(session_id: str, key: str) -> dict | list | int | None:
    """Read a workflow state entry from DynamoDB. Returns None if not found."""
    try:
        resp = _get_table().get_item(Key={"session_id": session_id, "state_key": key})
        item = resp.get("Item")
        if not item:
            return None
        return _from_decimal(item.get("data"))
    except Exception:
        logger.warning("Failed to load workflow state", extra={"key": key}, exc_info=True)
        return None


def save_structured_outputs(session_id: str, outputs: dict[str, dict]) -> None:
    """Persist all structured outputs from a single invocation.

    IMPORTANT: delay_candidates and delay_index are only written once
    (during Round 1 when they don't yet exist). Subsequent CO invocations
    during the delay optimization phase must NOT overwrite them — the
    candidate list and cursor are the source of truth for the sequential
    delay approval flow.
    """
    for agent_name, data in outputs.items():
        key_map = {
            "Impact Assessment Agent": "round1_ia",
            "Capacity & Optimization Agent": "round1_co",
            "Constraint Matching Agent": "funnel_results",
        }
        key = key_map.get(agent_name)
        if key:
            save_state(session_id, key, data)
            # Only seed delay candidates on first write (Round 1).
            # If delay_candidates already exists, skip — don't overwrite
            # the canonical list with a regenerated subset.
            if key == "round1_co" and "delay_candidates" in data:
                existing = load_state(session_id, "delay_candidates")
                if existing is None:
                    save_state(session_id, "delay_candidates", data["delay_candidates"])
                    save_state(session_id, "delay_index", 0)


def load_all_structured_outputs(session_id: str) -> dict[str, dict]:
    """Load all persisted structured outputs for a session."""
    result = {}
    ia = load_state(session_id, "round1_ia")
    if ia and isinstance(ia, dict):
        result["Impact Assessment Agent"] = ia
    co = load_state(session_id, "round1_co")
    if co and isinstance(co, dict):
        result["Capacity & Optimization Agent"] = co
    cm = load_state(session_id, "funnel_results")
    if cm and isinstance(cm, dict):
        result["Constraint Matching Agent"] = cm
    return result


def get_next_delay_candidate(session_id: str) -> dict | None:
    """Get the current delay candidate based on the stored index."""
    candidates = load_state(session_id, "delay_candidates")
    index = load_state(session_id, "delay_index")
    if not candidates or not isinstance(candidates, list):
        return None
    idx = index if isinstance(index, int) else 0
    if idx < len(candidates):
        return candidates[idx]
    return None


def advance_delay_index(session_id: str) -> int:
    """Increment the delay candidate index. Returns the new index."""
    index = load_state(session_id, "delay_index")
    new_idx = (index if isinstance(index, int) else 0) + 1
    save_state(session_id, "delay_index", new_idx)
    return new_idx


def save_phase(session_id: str, phase: str) -> None:
    """Persist the current workflow phase."""
    save_state(session_id, "current_phase", {"phase": phase})


def load_phase(session_id: str) -> str | None:
    """Load the persisted workflow phase."""
    data = load_state(session_id, "current_phase")
    if isinstance(data, dict):
        return data.get("phase")
    return None


def save_order_decision(session_id: str, order_id: str, decision: str, phase: str) -> None:
    """Record a planner's decision on an order (delay or funnel).

    Appends to the ``order_decisions`` list in workflow-state.
    Each entry: {order_id, decision, phase, timestamp}.
    """
    import time as _time

    decisions = load_state(session_id, "order_decisions")
    if not isinstance(decisions, list):
        decisions = []
    decisions.append({
        "order_id": order_id,
        "decision": decision,
        "phase": phase,
        "timestamp": int(_time.time()),
    })
    save_state(session_id, "order_decisions", decisions)
