#!/usr/bin/env python3
"""E2E test for AgentCore Memory session continuity.

Sends two messages with the same session ID. The second message
references context from the first — if memory works, the orchestrator
should remember the Florida hurricane disruption.

Uses boto3 Lambda invoke (bypasses Function URL auth).
"""

import json
import sys
import time
import uuid

import boto3
from botocore.config import Config

FUNCTION_NAME = "disruptionai-rest-proxy"
REGION = "us-east-1"
SESSION_ID = f"disruptionai-memory-test-{uuid.uuid4()}"

lambda_client = boto3.client(
    "lambda",
    region_name=REGION,
    config=Config(read_timeout=900, connect_timeout=10, retries={"max_attempts": 0}),
)


def send_message(message: str, session_id: str) -> str:
    """Invoke the REST proxy Lambda directly and return the response text."""
    print(f"\n{'='*60}")
    print(f"SENDING: {message[:80]}...")
    print(f"Session: {session_id}")
    print(f"{'='*60}")

    event = {
        "body": json.dumps({"message": message, "sessionId": session_id}),
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
    error = body.get("error")

    if error:
        print(f"ERROR: {error}")
    print(f"Response: {str(agent_reply)[:400]}{'...' if len(str(agent_reply)) > 400 else ''}")
    print(f"--- {len(str(agent_reply))} chars ---")

    return str(agent_reply)


def main():
    print(f"AgentCore Memory E2E Test")
    print(f"Function: {FUNCTION_NAME}")
    print(f"Session ID: {SESSION_ID}")

    # Message 1: Introduce a disruption scenario
    msg1 = (
        "There is a hurricane in Florida. "
        "The Florida plant needs to shut down immediately. "
        "Route all Florida production orders to the Ohio plant."
    )
    resp1 = send_message(msg1, SESSION_ID)

    if not resp1.strip():
        print("\nFAIL: Empty response to first message")
        sys.exit(1)

    print("\nWaiting 5 seconds before second message...")
    time.sleep(5)

    # Message 2: Reference the first message without repeating context
    msg2 = "What disruption event did I just tell you about?"
    resp2 = send_message(msg2, SESSION_ID)

    if not resp2.strip():
        print("\nFAIL: Empty response to second message")
        sys.exit(1)

    resp2_lower = resp2.lower()
    keywords = ["florida", "hurricane", "disruption", "plant"]
    found = [kw for kw in keywords if kw in resp2_lower]

    print(f"\n{'='*60}")
    print(f"MEMORY TEST RESULT")
    print(f"{'='*60}")
    print(f"Keywords found in response 2: {found}")

    if len(found) >= 2:
        print("PASS: Orchestrator remembered context from first message")
    elif len(found) == 1:
        print("PARTIAL: Some context retained, but weak signal")
    else:
        print("FAIL: Orchestrator did NOT remember the first message")

    sys.exit(0 if len(found) >= 2 else 1)


if __name__ == "__main__":
    main()
