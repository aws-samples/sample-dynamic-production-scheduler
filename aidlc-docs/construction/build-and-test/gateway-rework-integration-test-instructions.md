# Integration Test Instructions — Gateway Rework (Rework Cycle 2)

## Overview

Integration tests validate the end-to-end flow from agent through AgentCore Gateway to Lambda functions and DynamoDB. These tests require deployed infrastructure.

## Prerequisites

- All CDK stacks deployed (Phase 1 of build instructions)
- Gateway created and targets registered (Phase 3 of build instructions)
- Credential providers registered (Phase 3.5 of build instructions)
- Environment variables configured (Phase 5 of build instructions)

## Test Scenario 1: Cognito Token Acquisition

Verify agents can obtain OAuth2 tokens from Cognito.

```bash
# Test client_credentials grant
curl -s -X POST $COGNITO_TOKEN_ENDPOINT \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "grant_type=client_credentials&client_id=$COGNITO_APP_CLIENT_ID&client_secret=$COGNITO_APP_CLIENT_SECRET&scope=disruptionai-gateway/erp-data" \
  | python -m json.tool
```

Expected: JSON response with `access_token`, `token_type: "Bearer"`, `expires_in: 3600`.

Verify token contains correct scopes:

```bash
# Decode JWT payload (base64)
TOKEN=$(curl -s -X POST $COGNITO_TOKEN_ENDPOINT \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "grant_type=client_credentials&client_id=$COGNITO_APP_CLIENT_ID&client_secret=$COGNITO_APP_CLIENT_SECRET&scope=disruptionai-gateway/erp-data" \
  | python -c "import sys,json; print(json.load(sys.stdin)['access_token'])")

echo $TOKEN | cut -d. -f2 | base64 -d 2>/dev/null | python -m json.tool
```

Expected: `scope` field contains `disruptionai-gateway/erp-data`.


## Test Scenario 2: Gateway ERP Data Tool Invocation

Test the full path: Token -> Gateway -> Lambda -> DynamoDB -> Response.

### 2.1 Get Orders (Read Operation)

```bash
TOKEN=$(curl -s -X POST $COGNITO_TOKEN_ENDPOINT \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "grant_type=client_credentials&client_id=$COGNITO_APP_CLIENT_ID&client_secret=$COGNITO_APP_CLIENT_SECRET&scope=disruptionai-gateway/erp-data" \
  | python -c "import sys,json; print(json.load(sys.stdin)['access_token'])")

curl -s -X POST $GATEWAY_ENDPOINT \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "tool_name": "get_orders_tool",
    "arguments": {"plant": "Florida"}
  }' | python -m json.tool
```

Expected: JSON with `result` containing array of Florida plant orders.

### 2.2 Get Machine Capacity (Read Operation)

```bash
curl -s -X POST $GATEWAY_ENDPOINT \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "tool_name": "get_machine_capacity_tool",
    "arguments": {"machine_type": "Rolling Mill"}
  }' | python -m json.tool
```

Expected: JSON with `result` containing Rolling Mill capacity data.

### 2.3 Get Customers (Read Operation)

```bash
curl -s -X POST $GATEWAY_ENDPOINT \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "tool_name": "get_customers_tool",
    "arguments": {}
  }' | python -m json.tool
```

Expected: JSON with `result` containing customer records.


## Test Scenario 3: Gateway Audit Tool Invocation

### 3.1 Write Audit Entry

```bash
TOKEN=$(curl -s -X POST $COGNITO_TOKEN_ENDPOINT \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "grant_type=client_credentials&client_id=$COGNITO_APP_CLIENT_ID&client_secret=$COGNITO_APP_CLIENT_SECRET&scope=disruptionai-gateway/audit" \
  | python -c "import sys,json; print(json.load(sys.stdin)['access_token'])")

curl -s -X POST $GATEWAY_ENDPOINT \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "tool_name": "write_audit_entry_tool",
    "arguments": {
      "session_id": "integration-test-001",
      "agent": "integration-test",
      "action": "gateway_validation",
      "details": {"test": "integration", "gateway": "active"},
      "timestamp": "2026-03-20T12:00:00Z"
    }
  }' | python -m json.tool
```

Expected: JSON with `result` confirming write success.

### 3.2 Read Audit Trail

```bash
curl -s -X POST $GATEWAY_ENDPOINT \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "tool_name": "get_audit_trail_tool",
    "arguments": {"session_id": "integration-test-001"}
  }' | python -m json.tool
```

Expected: JSON with `result` containing the audit entry written in 3.1.


## Test Scenario 4: Authentication Enforcement

### 4.1 Request Without Token (Should Fail)

```bash
curl -s -X POST $GATEWAY_ENDPOINT \
  -H "Content-Type: application/json" \
  -d '{"tool_name": "get_orders_tool", "arguments": {"plant": "Florida"}}' \
  -w "\nHTTP Status: %{http_code}\n"
```

Expected: HTTP 401 Unauthorized.

### 4.2 Request With Invalid Token (Should Fail)

```bash
curl -s -X POST $GATEWAY_ENDPOINT \
  -H "Authorization: Bearer invalid-token-here" \
  -H "Content-Type: application/json" \
  -d '{"tool_name": "get_orders_tool", "arguments": {"plant": "Florida"}}' \
  -w "\nHTTP Status: %{http_code}\n"
```

Expected: HTTP 401 or 403.


## Test Scenario 5: Input Validation

### 5.1 Missing Required Field

```bash
TOKEN=$(curl -s -X POST $COGNITO_TOKEN_ENDPOINT \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "grant_type=client_credentials&client_id=$COGNITO_APP_CLIENT_ID&client_secret=$COGNITO_APP_CLIENT_SECRET&scope=disruptionai-gateway/erp-data" \
  | python -c "import sys,json; print(json.load(sys.stdin)['access_token'])")

curl -s -X POST $GATEWAY_ENDPOINT \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"tool_name": "get_order_by_id_tool", "arguments": {}}' \
  | python -m json.tool
```

Expected: JSON with `error` containing "Invalid input" (Pydantic validation).

### 5.2 Unknown Tool Name

```bash
curl -s -X POST $GATEWAY_ENDPOINT \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"tool_name": "nonexistent_tool", "arguments": {}}' \
  | python -m json.tool
```

Expected: JSON with `error` containing "Unknown tool".


## Test Scenario 6: Agent-to-Gateway End-to-End

Test a single agent connecting through the gateway:

```python
"""Quick integration test — run from orchestrator-agent directory."""
import os
from orchestrator_agent.config import OrchestratorSettings

settings = OrchestratorSettings()
print(f"Gateway URL: {settings.gateway_url}")
print(f"Token endpoint: {settings.cognito_token_endpoint}")
print(f"Client ID: {settings.cognito_client_id}")
print(f"ERP scope: {settings.erp_data_scope}")
print(f"Audit scope: {settings.audit_scope}")

# Verify config loads without error
assert settings.gateway_url, "gateway_url must be set"
assert settings.cognito_token_endpoint, "cognito_token_endpoint must be set"
assert settings.cognito_client_id, "cognito_client_id must be set"
print("Agent config validation: PASSED")
```

## Test Results Checklist

| Scenario | Test | Expected | Actual |
|----------|------|----------|--------|
| 1 | Cognito token acquisition | 200 + access_token | |
| 2.1 | Get orders via gateway | Orders array | |
| 2.2 | Get machine capacity | Capacity data | |
| 2.3 | Get customers | Customer records | |
| 3.1 | Write audit entry | Write success | |
| 3.2 | Read audit trail | Entry from 3.1 | |
| 4.1 | No token | 401 Unauthorized | |
| 4.2 | Invalid token | 401/403 | |
| 5.1 | Missing required field | Validation error | |
| 5.2 | Unknown tool | Unknown tool error | |
| 6 | Agent config validation | Config loads | |