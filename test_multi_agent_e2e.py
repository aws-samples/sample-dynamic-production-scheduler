#!/usr/bin/env python3
"""E2E test for multi-agent system with memory continuity.

Sends a disruption scenario that triggers the orchestrator to invoke
sub-agents (Impact Assessment, Capacity Optimization) and use MCP tools
(ERP Data, Audit). Then sends a follow-up to verify memory across turns.

Tests:
1. Orchestrator receives disruption and initiates Round 1
2. Sub-agents are invoked (Impact Assessment + Capacity Optimization)
3. MCP tools are used (ERP data queries, audit logging)
4. Session continuity — second message references first without repeating context
"""

import json
import sys
import time
import uuid

import requests

API_URL = "https://0tekmcy7lk.execute-api.us-east-1.amazonaws.com/prod/invoke"
SESSION_ID = f"disruptionai-multiagent-{uuid.uuid4()}"
TIMEOUT = 180  # seconds per request — sub-agent calls take longer


def send_message(message: str, session_id: str, label: str = "") -> str:
    """Send a message and return the full response text."""
    print(f"\n{'='*70}")
    print(f"[{label}] SENDING: {message[:100]}...")
    print(f"Session: {session_id}")
    print(f"{'='*70}")

    resp = requests.post(
        API_URL,
        json={"message": message, "sessionId": session_id},
        headers={"Content-Type": "application/json"},
        timeout=TIMEOUT,
        stream=True,
    )

    print(f"Status: {resp.status_code}")
    print(f"X-Session-Id: {resp.headers.get('X-Session-Id', 'N/A')}")

    full_text = ""
    for chunk in resp.iter_content(chunk_size=None, decode_unicode=True):
        if chunk:
            full_text += chunk
            print(chunk, end="", flush=True)

    print(f"\n--- Response length: {len(full_text)} chars ---")
    return full_text


def check_keywords(text: str, keywords: list[str], label: str) -> list[str]:
    """Check for keywords in response text."""
    text_lower = text.lower()
    found = [kw for kw in keywords if kw in text_lower]
    missing = [kw for kw in keywords if kw not in text_lower]
    print(f"\n[{label}] Keywords found: {found}")
    if missing:
        print(f"[{label}] Keywords missing: {missing}")
    return found


def main():
    print(f"Multi-Agent System E2E Test")
    print(f"API: {API_URL}")
    print(f"Session ID: {SESSION_ID}")
    print(f"Timeout per request: {TIMEOUT}s")

    results = {}

    # ---------------------------------------------------------------
    # Message 1: Trigger disruption + confirm Round 1
    # This should cause the orchestrator to invoke Impact Assessment
    # and Capacity Optimization sub-agents, which query ERP data via MCP
    # ---------------------------------------------------------------
    msg1 = (
        "There is a hurricane in Florida. The Florida plant must shut down now. "
        "Route all Florida orders to the Ohio plant. "
        "Yes, proceed with Round 1 intelligence gathering immediately."
    )
    resp1 = send_message(msg1, SESSION_ID, "MSG1-DISRUPTION+ROUND1")

    if not resp1.strip():
        print("\nFAIL: Empty response to message 1")
        sys.exit(1)

    # Check that sub-agents were invoked — response should mention
    # impact assessment results, capacity analysis, or order data
    r1_keywords = check_keywords(
        resp1,
        ["impact", "capacity", "order", "florida", "ohio", "plant", "priority"],
        "MSG1",
    )
    results["msg1_sub_agents"] = len(r1_keywords) >= 3

    print(f"\nWaiting 5 seconds before follow-up...")
    time.sleep(5)

    # ---------------------------------------------------------------
    # Message 2: Memory test — reference the disruption without context
    # ---------------------------------------------------------------
    msg2 = "What disruption are we dealing with and what have you found so far?"
    resp2 = send_message(msg2, SESSION_ID, "MSG2-MEMORY-CHECK")

    if not resp2.strip():
        print("\nFAIL: Empty response to message 2")
        sys.exit(1)

    r2_keywords = check_keywords(
        resp2,
        ["florida", "hurricane", "ohio"],
        "MSG2-MEMORY",
    )
    results["msg2_memory"] = len(r2_keywords) >= 2

    # ---------------------------------------------------------------
    # Results Summary
    # ---------------------------------------------------------------
    print(f"\n{'='*70}")
    print(f"MULTI-AGENT E2E TEST RESULTS")
    print(f"{'='*70}")

    all_pass = True
    for test_name, passed in results.items():
        status = "PASS" if passed else "FAIL"
        if not passed:
            all_pass = False
        print(f"  {test_name}: {status}")

    print(f"\nOverall: {'PASS' if all_pass else 'FAIL'}")

    # Check if sub-agents were actually invoked by looking for
    # specific data patterns (order numbers, capacity percentages, etc.)
    resp1_lower = resp1.lower()
    sub_agent_signals = []
    if any(w in resp1_lower for w in ["score", "priorit", "urgency", "tier"]):
        sub_agent_signals.append("Impact Assessment (scoring/priority data)")
    if any(w in resp1_lower for w in ["capacity", "utilization", "%", "dimension"]):
        sub_agent_signals.append("Capacity Optimization (capacity data)")
    if any(w in resp1_lower for w in ["order", "po-", "production order"]):
        sub_agent_signals.append("ERP Data MCP (order data)")
    if any(w in resp1_lower for w in ["audit", "logged", "recorded"]):
        sub_agent_signals.append("Audit MCP (audit logging)")

    if sub_agent_signals:
        print(f"\nSub-agent/MCP signals detected:")
        for sig in sub_agent_signals:
            print(f"  - {sig}")
    else:
        print(f"\nWARNING: No clear sub-agent invocation signals in response")
        print(f"  The orchestrator may have responded without invoking sub-agents")
        print(f"  Check CloudWatch logs for invoke_impact_assessment / invoke_capacity_optimization calls")

    sys.exit(0 if all_pass else 1)


if __name__ == "__main__":
    main()
