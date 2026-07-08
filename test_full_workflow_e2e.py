#!/usr/bin/env python3
"""Full workflow E2E test — Two-Persona Scenario (Rework 4).

Tests the complete disruption response workflow with plant-scoped sessions:
  1. Miami planner reports disruption, orchestrator runs Round 1
  2. Miami planner confirms proceed to Round 2
  3. Miami planner approves delays + constraint funnel
  4. Miami planner confirms transfer proposals
  5. Ohio planner receives and approves transfers
  6. Summary generation with final state

Uses boto3 Lambda invoke (bypasses Function URL auth) so we can test
with standard IAM credentials from the environment.
"""

import json
import sys
import time
import uuid

import boto3
from botocore.config import Config

FUNCTION_NAME = "disruptionai-rest-proxy"
REGION = "us-east-1"

# Two separate sessions — one per planner
MIAMI_SESSION = f"disruptionai-miami-{uuid.uuid4()}"
OHIO_SESSION = f"disruptionai-ohio-{uuid.uuid4()}"

lambda_client = boto3.client(
    "lambda",
    region_name=REGION,
    config=Config(read_timeout=900, connect_timeout=10, retries={"max_attempts": 0}),
)


def send(message: str, label: str, session_id: str, plant: str = "") -> str:
    """Invoke the REST proxy Lambda directly and return the response text."""
    print(f"\n{'='*70}")
    print(f"[{label}] SENDING ({plant or 'no-plant'}):")
    print(f"  {message[:140]}{'...' if len(message) > 140 else ''}")
    print(f"  Session: {session_id[:50]}...")
    print(f"{'='*70}")

    payload_body = {"message": message, "sessionId": session_id}
    if plant:
        payload_body["plant"] = plant

    event = {
        "body": json.dumps(payload_body),
        "requestContext": {"http": {"method": "POST"}},
    }

    resp = lambda_client.invoke(
        FunctionName=FUNCTION_NAME,
        InvocationType="RequestResponse",
        Payload=json.dumps(event),
    )

    payload = json.loads(resp["Payload"].read())
    status = payload.get("statusCode", 0)
    body_raw = payload.get("body", "")

    print(f"Lambda status: {status}")

    try:
        body = json.loads(body_raw)
    except (json.JSONDecodeError, TypeError):
        body = {"message": body_raw}

    agent_reply = body.get("message", body_raw)
    resp_session = body.get("sessionId", "")
    error = body.get("error")

    if error:
        print(f"ERROR: {error}")
    print(f"Response session: {resp_session[:50]}...")
    print(f"Response: {str(agent_reply)[:500]}{'...' if len(str(agent_reply)) > 500 else ''}")
    print(f"--- {len(str(agent_reply))} chars ---")

    if not str(agent_reply).strip():
        print(f"FATAL: Empty response at [{label}]")
        sys.exit(1)

    return str(agent_reply)


def kw(text: str, words: list[str]) -> list[str]:
    """Return which keywords appear in text (case-insensitive)."""
    t = text.lower()
    return [w for w in words if w in t]


def main():
    print("Two-Persona Full Workflow E2E Test")
    print(f"Miami session: {MIAMI_SESSION}")
    print(f"Ohio session:  {OHIO_SESSION}")

    results = {}

    # ==================================================================
    # PHASE 1: Miami planner reports disruption + Round 1
    # ==================================================================
    r1 = send(
        "There is a hurricane in Florida. The Miami plant must shut down immediately. "
        "All active production orders at the Florida plant are impacted. "
        "Yes, proceed with Round 1 intelligence gathering now.",
        "MIAMI-MSG1-ROUND1",
        MIAMI_SESSION,
        plant="Florida",
    )
    r1_hits = kw(r1, [
        "impact", "capacity", "order", "florida", "ohio",
        "rolling mill", "priority", "hurricane",
    ])
    results["miami_round1_sub_agents"] = len(r1_hits) >= 4
    print(f"\n  Round 1 keywords ({len(r1_hits)}): {r1_hits}")

    time.sleep(3)

    # ==================================================================
    # PHASE 2: Miami planner proceeds to Round 2 (delays)
    # ==================================================================
    r2 = send(
        "Yes, proceed to Round 2. Start with the delay phase - identify Ohio orders "
        "that can be delayed to free capacity for the Florida orders.",
        "MIAMI-MSG2-DELAYS",
        MIAMI_SESSION,
        plant="Florida",
    )
    r2_hits = kw(r2, ["delay", "slack", "candidate", "capacity", "ohio", "free", "p3"])
    results["miami_round2_delays"] = len(r2_hits) >= 3
    print(f"\n  Delay phase keywords ({len(r2_hits)}): {r2_hits}")

    time.sleep(3)

    # ==================================================================
    # PHASE 3: Miami planner approves delays + constraint funnel
    # ==================================================================
    r3 = send(
        "Approved. Delay those candidates. Now proceed to the constraint funnel - "
        "run the 4-layer constraint matching for each Florida order to determine "
        "which ones can be rerouted to Ohio.",
        "MIAMI-MSG3-FUNNEL",
        MIAMI_SESSION,
        plant="Florida",
    )
    r3_hits = kw(r3, [
        "constraint", "funnel", "layer", "reroute", "feasib",
        "machine", "material", "schedule", "po-", "transfer",
    ])
    results["miami_constraint_funnel"] = len(r3_hits) >= 3
    print(f"\n  Constraint funnel keywords ({len(r3_hits)}): {r3_hits}")

    time.sleep(3)

    # ==================================================================
    # PHASE 4: Miami planner confirms transfer proposals
    # ==================================================================
    r4 = send(
        "Approved. I confirm all feasible orders for transfer to Ohio. "
        "Please send these as transfer requests to the Ohio planner for approval.",
        "MIAMI-MSG4-CONFIRM-TRANSFERS",
        MIAMI_SESSION,
        plant="Florida",
    )
    r4_hits = kw(r4, [
        "transfer", "ohio", "approval", "request", "confirm",
        "sent", "pending", "planner",
    ])
    results["miami_transfer_confirmation"] = len(r4_hits) >= 3
    print(f"\n  Transfer confirmation keywords ({len(r4_hits)}): {r4_hits}")

    time.sleep(3)

    # ==================================================================
    # PHASE 5: Ohio planner session — receives and approves transfers
    # ==================================================================
    r5 = send(
        "I'm the Ohio planner. I understand there are transfer requests from the "
        "Miami plant due to a hurricane disruption. Show me the pending transfer "
        "requests and the capacity impact on my plant.",
        "OHIO-MSG1-VIEW-TRANSFERS",
        OHIO_SESSION,
        plant="Ohio",
    )
    r5_hits = kw(r5, [
        "ohio", "capacity", "transfer", "florida", "order",
        "rolling mill", "utilization", "hurricane",
    ])
    results["ohio_receives_context"] = len(r5_hits) >= 3
    print(f"\n  Ohio context keywords ({len(r5_hits)}): {r5_hits}")

    time.sleep(3)

    r6 = send(
        "I approve all the transfer requests. Absorb the critical Florida orders "
        "into Ohio production. De-prioritize our P3 orders if needed to make room.",
        "OHIO-MSG2-APPROVE-TRANSFERS",
        OHIO_SESSION,
        plant="Ohio",
    )
    r6_hits = kw(r6, [
        "approved", "transfer", "absorb", "ohio", "capacity",
        "de-priorit", "defer", "p3", "accept",
    ])
    results["ohio_approves_transfers"] = len(r6_hits) >= 3
    print(f"\n  Ohio approval keywords ({len(r6_hits)}): {r6_hits}")

    time.sleep(3)

    # ==================================================================
    # PHASE 6: Summary — request from Miami planner
    # ==================================================================
    r7 = send(
        "Please provide a complete executive summary of the entire disruption "
        "response - what happened, what decisions were made, which orders are "
        "being transferred to Ohio, which are delayed or suspended, and the "
        "final capacity state of both plants.",
        "MIAMI-MSG5-SUMMARY",
        MIAMI_SESSION,
        plant="Florida",
    )
    r7_hits = kw(r7, [
        "summary", "florida", "ohio", "hurricane", "transfer",
        "delay", "order", "decision", "capacity", "suspend",
    ])
    results["final_summary"] = len(r7_hits) >= 4
    print(f"\n  Summary keywords ({len(r7_hits)}): {r7_hits}")

    # ==================================================================
    # RESULTS
    # ==================================================================
    print(f"\n{'='*70}")
    print("TWO-PERSONA FULL WORKFLOW E2E RESULTS")
    print(f"{'='*70}")

    all_pass = True
    for name, passed in results.items():
        status = "PASS" if passed else "FAIL"
        if not passed:
            all_pass = False
        print(f"  {name}: {status}")

    # Verify plant passthrough worked
    all_text = (r1 + r2 + r3 + r4 + r5 + r6 + r7).lower()

    print(f"\nPlant-scoped verification:")
    miami_scoped = any(w in (r1 + r2 + r3 + r4).lower() for w in ["miami", "florida"])
    ohio_scoped = any(w in (r5 + r6).lower() for w in ["ohio"])
    print(f"  Miami session mentions Miami/Florida: {'YES' if miami_scoped else 'NO'}")
    print(f"  Ohio session mentions Ohio: {'YES' if ohio_scoped else 'NO'}")

    # Detect agents/tools across all messages
    agents_detected = []
    if any(w in all_text for w in ["impact assessment", "priorit", "urgency"]):
        agents_detected.append("Impact Assessment Agent")
    if any(w in all_text for w in ["capacity", "utilization", "rolling mill", "surplus"]):
        agents_detected.append("Capacity Optimization Agent")
    if any(w in all_text for w in ["constraint", "funnel", "4-layer", "layer 1"]):
        agents_detected.append("Constraint Matching Agent")
    if any(w in all_text for w in ["po-20", "production order", "steel"]):
        agents_detected.append("ERP Data MCP")
    if any(w in all_text for w in ["audit", "logged", "recorded"]):
        agents_detected.append("Audit MCP")

    print(f"\nAgents/tools detected:")
    for a in agents_detected:
        print(f"  + {a}")

    expected = {
        "Impact Assessment Agent",
        "Capacity Optimization Agent",
        "Constraint Matching Agent",
        "ERP Data MCP",
    }
    missing = expected - set(agents_detected)
    if missing:
        print(f"\nWARNING — not detected (check CloudWatch): {missing}")

    # Verify two-persona features
    print(f"\nTwo-persona feature checks:")
    has_transfer_flow = any(w in all_text for w in ["transfer request", "transfer to ohio", "pending transfer"])
    has_ohio_approval = any(w in all_text for w in ["approve", "accept", "absorb"])
    has_deprioritize = any(w in all_text for w in ["de-priorit", "defer", "deprioritiz"])
    print(f"  Transfer flow detected: {'YES' if has_transfer_flow else 'NO'}")
    print(f"  Ohio approval detected: {'YES' if has_ohio_approval else 'NO'}")
    print(f"  De-prioritization detected: {'YES' if has_deprioritize else 'NO'}")

    print(f"\nOverall: {'PASS' if all_pass else 'FAIL'}")
    sys.exit(0 if all_pass else 1)


if __name__ == "__main__":
    main()
