# Security Test Instructions — Gateway Rework (Rework Cycle 2)

## Overview

Security tests validate compliance with SECURITY-01 through SECURITY-15 for the gateway migration. These tests verify authentication enforcement, least-privilege IAM, input validation, error handling, and logging.

## 1. Authentication Tests (SECURITY-08, SECURITY-12)

### 1.1 JWT Validation — No Token

```bash
curl -s -X POST $GATEWAY_ENDPOINT \
  -H "Content-Type: application/json" \
  -d '{"tool_name": "get_orders_tool", "arguments": {"plant": "Florida"}}' \
  -w "\nHTTP Status: %{http_code}\n"
```

Expected: HTTP 401. Gateway rejects unauthenticated requests.

### 1.2 JWT Validation — Expired Token

Obtain a token, wait for expiry (3600s), then retry. Alternatively, craft an expired JWT.

Expected: HTTP 401. Gateway rejects expired tokens.

### 1.3 JWT Validation — Wrong Audience

Create a token from a different Cognito App Client (different audience claim).

Expected: HTTP 401 or 403. Gateway rejects tokens with wrong audience.

### 1.4 No Hardcoded Credentials (SECURITY-12)

```bash
# Scan all generated code for hardcoded secrets
grep -rn "client_secret\|password\|secret_key\|api_key" \
  erp-data-mcp/src/ audit-mcp/src/ \
  orchestrator-agent/src/ impact-assessment-agent/src/ \
  capacity-optimization-agent/src/ constraint-matching-agent/src/ \
  infrastructure/lib/ infrastructure/scripts/ \
  --include="*.py" --include="*.ts" \
  | grep -v "\.pyc" | grep -v "node_modules" \
  | grep -v "test_" | grep -v "__pycache__"
```

Expected: No hardcoded credential values. Only references to environment variables or parameter names.

## 2. Least-Privilege IAM Tests (SECURITY-06)

### 2.1 ERP Data Lambda Role — Verify Scoped Permissions

```bash
# Get the role name from CDK output
ROLE_NAME="disruptionai-erp-data-mcp-role"

aws iam list-role-policies --role-name $ROLE_NAME --output json
aws iam get-role-policy --role-name $ROLE_NAME --policy-name CloudWatchLogs --output json
aws iam get-role-policy --role-name $ROLE_NAME --policy-name DynamoDBReadOnly --output json
aws iam get-role-policy --role-name $ROLE_NAME --policy-name DynamoDBReadWrite --output json
```

Verify:
- CloudWatchLogs: Only `logs:CreateLogStream`, `logs:PutLogEvents` on specific log group
- DynamoDBReadOnly: Only `GetItem`, `Query`, `Scan` on capacity, manpower, materials, customers tables
- DynamoDBReadWrite: Adds `PutItem`, `UpdateItem` only on orders and tracker tables
- No wildcard resources or actions

### 2.2 Audit Lambda Role — Verify Scoped Permissions

```bash
ROLE_NAME="disruptionai-audit-mcp-role"

aws iam list-role-policies --role-name $ROLE_NAME --output json
aws iam get-role-policy --role-name $ROLE_NAME --policy-name DynamoDBAuditReadWrite --output json
```

Verify:
- Only `GetItem`, `Query`, `PutItem` on audit table and audit index
- No access to other DynamoDB tables

### 2.3 Gateway Management Role — No Wildcard Actions

```bash
ROLE_NAME="disruptionai-gateway-management-role"

aws iam list-role-policies --role-name $ROLE_NAME --output json
```

Verify: No `*` in Action fields. Only specific bedrock-agentcore and lambda actions.

## 3. Input Validation Tests (SECURITY-05)

### 3.1 SQL/NoSQL Injection Attempt

```bash
TOKEN=$(curl -s -X POST $COGNITO_TOKEN_ENDPOINT \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "grant_type=client_credentials&client_id=$COGNITO_APP_CLIENT_ID&client_secret=$COGNITO_APP_CLIENT_SECRET&scope=disruptionai-gateway/erp-data" \
  | python -c "import sys,json; print(json.load(sys.stdin)['access_token'])")

curl -s -X POST $GATEWAY_ENDPOINT \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"tool_name": "get_order_by_id_tool", "arguments": {"order_id": "'; DROP TABLE orders;--"}}' \
  | python -m json.tool
```

Expected: Pydantic validation rejects or DynamoDB treats as literal string. No injection.

### 3.2 Oversized Payload

```bash
LARGE=$(python -c "print('A' * 100000)")
curl -s -X POST $GATEWAY_ENDPOINT \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d "{\"tool_name\": \"get_order_by_id_tool\", \"arguments\": {\"order_id\": \"$LARGE\"}}" \
  -w "\nHTTP Status: %{http_code}\n"
```

Expected: Rejected by gateway or Lambda with appropriate error.

## 4. Error Handling Tests (SECURITY-09, SECURITY-15)

### 4.1 No Stack Traces in Error Responses

```bash
curl -s -X POST $GATEWAY_ENDPOINT \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"tool_name": "get_orders_tool", "arguments": {"plant": "InvalidPlant"}}' \
  | python -m json.tool
```

Verify: Response contains no Python tracebacks, file paths, or internal details.

### 4.2 Fail-Closed Behavior

Verify Lambda handler returns `{"error": "Internal server error"}` on unexpected exceptions (covered by unit tests).

## 5. Logging Tests (SECURITY-03, SECURITY-14)

### 5.1 Lambda CloudWatch Log Groups Exist

```bash
aws logs describe-log-groups \
  --log-group-name-prefix "/aws/lambda/disruptionai-" \
  --query "logGroups[].{name:logGroupName, retention:retentionInDays}" \
  --output table
```

Expected:
- `/aws/lambda/disruptionai-erp-data-mcp` with 90-day retention
- `/aws/lambda/disruptionai-audit-mcp` with 90-day retention

### 5.2 Gateway Log Group Exists

```bash
aws logs describe-log-groups \
  --log-group-name-prefix "/aws/bedrock-agentcore/gateway/" \
  --query "logGroups[].{name:logGroupName, retention:retentionInDays}" \
  --output table
```

Expected: Gateway log group with 90-day retention.

### 5.3 Structured Log Format

After invoking a tool, check Lambda logs:

```bash
aws logs filter-log-events \
  --log-group-name "/aws/lambda/disruptionai-erp-data-mcp" \
  --filter-pattern "request_id" \
  --limit 5 \
  --query "events[].message" \
  --output text
```

Expected: Logs contain `request_id`, `tool_name`, structured JSON format.

## 6. Encryption Tests (SECURITY-01)

### 6.1 DynamoDB Encryption at Rest

```bash
for TABLE in disruptionai-orders disruptionai-capacity disruptionai-manpower \
  disruptionai-materials disruptionai-customers disruptionai-tracker disruptionai-audit; do
  echo -n "$TABLE: "
  aws dynamodb describe-table --table-name $TABLE \
    --query "Table.SSEDescription.Status" --output text
done
```

Expected: All tables show `ENABLED` (AWS managed encryption).

## Security Test Checklist

| Rule | Test | Expected | Actual |
|------|------|----------|--------|
| SECURITY-01 | DynamoDB encryption | ENABLED | |
| SECURITY-03 | Structured logging | request_id in logs | |
| SECURITY-05 | Injection attempt | Rejected/literal | |
| SECURITY-06 | IAM least-privilege | No wildcards | |
| SECURITY-08 | No-token request | 401 | |
| SECURITY-08 | Invalid token | 401/403 | |
| SECURITY-09 | Error response | No stack traces | |
| SECURITY-12 | Credential scan | No hardcoded secrets | |
| SECURITY-14 | Log retention | 90 days | |
| SECURITY-15 | Fail-closed | Generic error | |
