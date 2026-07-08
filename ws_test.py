#!/usr/bin/env python3
"""Quick WebSocket smoke test for the disruption workflow.

WARNING: This is a development/test utility only. Do not use in production.
Output may contain response data from the system under test.

The API Gateway WebSocket has a 29s integration timeout, so the Lambda's
synchronous return will time out.  However the Lambda continues running
(5-min timeout) and pushes the real response back via post_to_connection.
This script ignores the gateway timeout message and keeps listening.
"""

import asyncio
import json
import sys

WS_URL = "wss://x5u9j1d0p7.execute-api.us-east-1.amazonaws.com/prod"
LISTEN_TIMEOUT = 300  # 5 minutes — match Lambda timeout


async def listen(ws, label=""):
    """Listen for stream_token messages until done=true.

    Collects all stream_token text, skips gateway timeouts and
    non-stream messages (phase_update, agent_switch), and only
    returns when done=true is received.
    """
    tokens = []
    try:
        while True:
            raw = await asyncio.wait_for(ws.recv(), timeout=LISTEN_TIMEOUT)
            try:
                msg = json.loads(raw)
            except json.JSONDecodeError:
                print(f"<<< [{label}] (non-JSON) {raw}\n")
                continue

            # Skip API Gateway 29s integration timeout
            if msg.get("message") == "Endpoint request timed out":
                print(f"   (API Gateway 29s timeout — Lambda still running, waiting...)\n")
                continue

            msg_type = msg.get("type", "unknown")

            if msg_type == "stream_token":
                payload = msg.get("payload", {})
                token = payload.get("token", "")
                done = payload.get("done", False)
                mid = payload.get("messageId", "?")
                if token:
                    tokens.append(token)
                    sys.stdout.write(token)
                    sys.stdout.flush()
                if done:
                    print(f"\n\n<<< [{label}] stream complete (messageId={mid}, {len(tokens)} chunks)")
                    return {"type": "stream_token", "full_text": "".join(tokens), "chunks": len(tokens)}
            elif msg_type == "phase_update":
                phase = msg.get("payload", {}).get("phase", "?")
                print(f"   [{label}] phase_update: {phase}")
                # Don't return — keep listening for done signal
                continue
            elif msg_type == "agent_switch":
                agent = msg.get("payload", {}).get("agent", "?")
                print(f"   [{label}] agent_switch: {agent}")
                # Don't return — keep listening for done signal
                continue
            elif msg_type == "error":
                err = msg.get("payload", {}).get("message", msg.get("data", str(msg)))
                print(f"<<< [{label}] ERROR: {err}\n")
                return msg
            else:
                print(f"<<< [{label}] other: {json.dumps(msg)}")
                # Don't return on unknown types — keep listening
                continue
    except asyncio.TimeoutError:
        if tokens:
            print(f"\n\n<<< [{label}] timeout after {len(tokens)} chunks received")
            return {"type": "stream_token", "full_text": "".join(tokens), "chunks": len(tokens)}
        print(f"   (No response after {LISTEN_TIMEOUT}s)\n")
        return None


async def main():
    import websockets

    print(f"Connecting to {WS_URL} ...")
    async with websockets.connect(WS_URL, ping_interval=30, ping_timeout=120) as ws:
        print("Connected.\n")

        # Step 1: trigger disruption workflow
        msg1 = {
            "action": "sendMessage",
            "data": (
                "A hurricane has disrupted the Florida plant. "
                "Assess impact on all active Florida production orders."
            ),
        }
        print(f">>> {json.dumps(msg1, indent=2)}\n")
        await ws.send(json.dumps(msg1))

        resp = await listen(ws, "step1")
        if resp:
            print(f"\n=== Step 1 response received ===\n")

        # Small delay to let Lambda finish before sending step 2
        await asyncio.sleep(2)

        # Step 2: confirm to proceed with the workflow
        msg2 = {
            "action": "sendMessage",
            "data": "Yes, proceed with the full disruption response workflow.",
        }
        print(f"\n>>> {json.dumps(msg2, indent=2)}\n")
        await ws.send(json.dumps(msg2))

        resp2 = await listen(ws, "step2")
        if resp2:
            print(f"\n=== Step 2 response received ===\n")
            if isinstance(resp2, dict) and resp2.get("type") == "stream_token":
                print(f"Full text length: {len(resp2.get('full_text', ''))}, chunks: {resp2.get('chunks', 0)}")
            elif isinstance(resp2, dict):
                print(json.dumps(resp2, indent=2))
        else:
            print("=== No step 2 response ===")

    print("\nDone.")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nInterrupted.")
        sys.exit(0)
