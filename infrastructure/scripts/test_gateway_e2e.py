#!/usr/bin/env python3
"""End-to-end test for AgentCore Gateway via MCP JSON-RPC protocol.

WARNING: This is a development/test utility only. Do not use in production.
Output may contain response data from the system under test.

Tests:
1. Cognito token acquisition
2. MCP initialize handshake
3. tools/list to verify tool registration
4. tools/call on erp-data-mcp target (get_workforce_tool)
5. tools/call on audit-mcp target (get_audit_trail_tool)

IMPORTANT: Gateway returns plain JSON-RPC responses (NOT SSE).
Tool names use THREE underscores: {target-name}___{tool-name}
Arguments must include action_name for Lambda dispatch routing.
"""

import json
import os
import sys

import requests

GATEWAY_URL = "https://disruptionai-mcp-gateway-p9qpkebcdw.gateway.bedrock-agentcore.us-east-1.amazonaws.com/mcp"
TOKEN_URL = os.environ.get("COGNITO_TOKEN_ENDPOINT", "REPLACE_WITH_COGNITO_TOKEN_URL")
CLIENT_ID = os.environ.get("COGNITO_CLIENT_ID", "REPLACE_WITH_CLIENT_ID")
CLIENT_SECRET = os.environ.get("COGNITO_CLIENT_SECRET", "REPLACE_WITH_CLIENT_SECRET")
SCOPES = "disruptionai-gateway/audit disruptionai-gateway/erp-data"


def get_token():
    r = requests.post(TOKEN_URL, data={
        "grant_type": "client_credentials",
        "client_id": CLIENT_ID,
        "client_secret": CLIENT_SECRET,
        "scope": SCOPES,
    }, timeout=10)
    r.raise_for_status()
    return r.json()["access_token"]


def send_mcp(token, payload, timeout=30):
    """Send MCP JSON-RPC request and return parsed JSON response."""
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
        "Accept": "application/json",
    }
    r = requests.post(GATEWAY_URL, json=payload, headers=headers, timeout=timeout)
    if r.status_code != 200:
        return {"_http_status": r.status_code, "_body": r.text[:500]}
    return r.json()


def main():
    passed = 0
    failed = 0

    # 1. Token
    print("=" * 60)
    print("TEST 1: Cognito Token Acquisition")
    try:
        token = get_token()
        print(f"  PASS - token obtained ({len(token)} chars)")
        passed += 1
    except Exception as e:
        print(f"  FAIL - {e}")
        failed += 1
        sys.exit(1)

    # 2. Initialize
    print("\nTEST 2: MCP Initialize")
    init_resp = send_mcp(token, {
        "jsonrpc": "2.0", "id": 1, "method": "initialize",
        "params": {
            "protocolVersion": "2025-03-26",
            "capabilities": {},
            "clientInfo": {"name": "e2e-test", "version": "1.0.0"},
        }
    })
    if "result" in init_resp:
        print(f"  PASS - server: {init_resp['result'].get('serverInfo', {}).get('name', 'unknown')}")
        passed += 1
    else:
        print(f"  FAIL - {json.dumps(init_resp)[:300]}")
        failed += 1

    # Send initialized notification (fire-and-forget)
    try:
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
            "Accept": "application/json",
        }
        requests.post(GATEWAY_URL,
                      json={"jsonrpc": "2.0", "method": "notifications/initialized"},
                      headers=headers, timeout=5)
    except Exception:
        pass

    # 3. tools/list
    print("\nTEST 3: tools/list")
    list_resp = send_mcp(token, {
        "jsonrpc": "2.0", "id": 2, "method": "tools/list", "params": {}
    })
    if "result" in list_resp:
        tools = list_resp["result"].get("tools", [])
        tool_names = [t["name"] for t in tools]
        print(f"  PASS - {len(tools)} tools found")
        for name in sorted(tool_names):
            print(f"    - {name}")
        passed += 1
    else:
        print(f"  FAIL - {json.dumps(list_resp)[:300]}")
        failed += 1

    # 4. tools/call - ERP data (get_workforce_tool — action_name required)
    erp_tool = "erp-data-mcp-target___get_workforce_tool"
    print(f"\nTEST 4: tools/call - {erp_tool}")
    call_resp = send_mcp(token, {
        "jsonrpc": "2.0", "id": 3, "method": "tools/call",
        "params": {
            "name": erp_tool,
            "arguments": {"action_name": "get_workforce_tool"}
        }
    }, timeout=60)
    if "result" in call_resp:
        content = call_resp["result"].get("content", [])
        if content:
            text = content[0].get("text", "")[:300]
            print(f"  PASS - got response: {text}")
        else:
            print(f"  PASS - result: {json.dumps(call_resp['result'])[:300]}")
        passed += 1
    elif "error" in call_resp:
        print(f"  FAIL - error: {json.dumps(call_resp['error'])[:500]}")
        failed += 1
    else:
        print(f"  FAIL - unexpected: {json.dumps(call_resp)[:500]}")
        failed += 1

    # 5. tools/call - Audit (get_audit_trail_tool — needs action_name + session_id)
    audit_tool = "audit-mcp-target___get_audit_trail_tool"
    print(f"\nTEST 5: tools/call - {audit_tool}")
    call_resp2 = send_mcp(token, {
        "jsonrpc": "2.0", "id": 4, "method": "tools/call",
        "params": {
            "name": audit_tool,
            "arguments": {
                "action_name": "get_audit_trail_tool",
                "session_id": "test-e2e-session-001"
            }
        }
    }, timeout=60)
    if "result" in call_resp2:
        content = call_resp2["result"].get("content", [])
        if content:
            text = content[0].get("text", "")[:300]
            print(f"  PASS - got response: {text}")
        else:
            print(f"  PASS - result: {json.dumps(call_resp2['result'])[:300]}")
        passed += 1
    elif "error" in call_resp2:
        print(f"  FAIL - error: {json.dumps(call_resp2['error'])[:500]}")
        failed += 1
    else:
        print(f"  FAIL - unexpected: {json.dumps(call_resp2)[:500]}")
        failed += 1

    # Summary
    print("\n" + "=" * 60)
    print(f"RESULTS: {passed} passed, {failed} failed out of {passed + failed}")
    print("=" * 60)
    sys.exit(1 if failed > 0 else 0)


if __name__ == "__main__":
    main()
