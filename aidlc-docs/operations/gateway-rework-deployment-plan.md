# Deployment Plan — Gateway Rework (Rework Cycle 2)

## Overview

Step-by-step deployment guide for migrating erp-data-mcp and audit-mcp from direct AgentCore Runtime to AgentCore Gateway with Lambda targets and Cognito OAuth.

## Pre-Deployment Checklist

- [ ] All unit tests pass locally (Lambda handlers, CDK stacks, script syntax)
- [ ] CDK synth succeeds without errors
- [ ] AWS CLI configured for account `058264253938`, region `us-east-1`
- [ ] Current system is stable (all 6 agents READY on AgentCore Runtime)
- [ ] Backup: Note current agent runtime IDs from aidlc-state.md

## Deployment Sequence

### Step 1: Deploy CDK Infrastructure

```bash
cd infrastructure
npm install
npm run build
npx cdk deploy DisruptionAI-Cognito --require-approval never
npx cdk deploy DisruptionAI-McpLambda --require-approval never
npx cdk deploy DisruptionAI-GatewayIam --require-approval never
npx cdk deploy DisruptionAI-IAM --require-approval never
```

Capture outputs:
```bash
COGNITO_USER_POOL_ID=$(aws cloudformation describe-stacks \
  --stack-name DisruptionAI-Cognito \
  --query "Stacks[0].Outputs[?OutputKey=='UserPoolId'].OutputValue" --output text)

COGNITO_APP_CLIENT_ID=$(aws cloudformation describe-stacks \
  --stack-name DisruptionAI-Cognito \
  --query "Stacks[0].Outputs[?OutputKey=='AppClientId'].OutputValue" --output text)

COGNITO_TOKEN_ENDPOINT=$(aws cloudformation describe-stacks \
  --stack-name DisruptionAI-Cognito \
  --query "Stacks[0].Outputs[?OutputKey=='TokenEndpoint'].OutputValue" --output text)

ERP_DATA_LAMBDA_ARN=$(aws cloudformation describe-stacks \
  --stack-name DisruptionAI-McpLambda \
  --query "Stacks[0].Outputs[?OutputKey=='ErpDataLambdaArn'].OutputValue" --output text)

AUDIT_LAMBDA_ARN=$(aws cloudformation describe-stacks \
  --stack-name DisruptionAI-McpLambda \
  --query "Stacks[0].Outputs[?OutputKey=='AuditLambdaArn'].OutputValue" --output text)

COGNITO_APP_CLIENT_SECRET=$(aws cognito-idp describe-user-pool-client \
  --user-pool-id $COGNITO_USER_POOL_ID \
  --client-id $COGNITO_APP_CLIENT_ID \
  --query 'UserPoolClient.ClientSecret' --output text)
```

### Step 2: Create Gateway and Targets

Note: Uses `bedrock-agentcore-control` boto3 client (not `bedrock-agentcore`).
Gateway management role ARN is required for gateway creation.

```bash
GATEWAY_ROLE_ARN=$(aws cloudformation describe-stacks \
  --stack-name DisruptionAI-GatewayIam \
  --query "Stacks[0].Outputs[?OutputKey=='GatewayManagementRoleArn'].OutputValue" --output text)

python3 infrastructure/scripts/create_gateway.py \
  --cognito-user-pool-id $COGNITO_USER_POOL_ID \
  --cognito-app-client-id $COGNITO_APP_CLIENT_ID \
  --role-arn $GATEWAY_ROLE_ARN

GATEWAY_ID=$(python3 -c "import json; print(json.load(open('infrastructure/scripts/.gateway-config.json'))['gateway_id'])")
GATEWAY_ARN=$(python3 -c "import json; print(json.load(open('infrastructure/scripts/.gateway-config.json'))['gateway_arn'])")
GATEWAY_ENDPOINT=$(python3 -c "import json; print(json.load(open('infrastructure/scripts/.gateway-config.json'))['endpoint'])")

python3 infrastructure/scripts/create_erp_data_target.py \
  --gateway-id $GATEWAY_ID --lambda-arn $ERP_DATA_LAMBDA_ARN

python3 infrastructure/scripts/create_audit_target.py \
  --gateway-id $GATEWAY_ID --lambda-arn $AUDIT_LAMBDA_ARN

python3 infrastructure/scripts/gateway_observability.py \
  --gateway-id $GATEWAY_ID --gateway-arn $GATEWAY_ARN
```

### Step 3: Validate Cognito Token Flow

Agents authenticate to the gateway by obtaining Cognito client_credentials
tokens directly. This step validates the token flow works for all agents.

```bash
python3 infrastructure/scripts/cognito_credentials_provider.py \
  --cognito-token-endpoint $COGNITO_TOKEN_ENDPOINT \
  --cognito-app-client-id $COGNITO_APP_CLIENT_ID \
  --cognito-app-client-secret $COGNITO_APP_CLIENT_SECRET
```

### Step 4: Update Cross-Agent Permissions

```bash
bash infrastructure/scripts/apply-cross-agent-permissions.sh
```

### Step 5: Validate Gateway (Before Agent Cutover)

```bash
# Get token
TOKEN=$(curl -s -X POST $COGNITO_TOKEN_ENDPOINT \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "grant_type=client_credentials&client_id=$COGNITO_APP_CLIENT_ID&client_secret=$COGNITO_APP_CLIENT_SECRET&scope=disruptionai-gateway/erp-data" \
  | python -c "import sys,json; print(json.load(sys.stdin)['access_token'])")

# Test ERP data tool
curl -s -X POST $GATEWAY_ENDPOINT \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"tool_name": "get_orders_tool", "arguments": {"plant": "Florida"}}' \
  | python -m json.tool

# Test audit tool
TOKEN_AUDIT=$(curl -s -X POST $COGNITO_TOKEN_ENDPOINT \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "grant_type=client_credentials&client_id=$COGNITO_APP_CLIENT_ID&client_secret=$COGNITO_APP_CLIENT_SECRET&scope=disruptionai-gateway/audit" \
  | python -c "import sys,json; print(json.load(sys.stdin)['access_token'])")

curl -s -X POST $GATEWAY_ENDPOINT \
  -H "Authorization: Bearer $TOKEN_AUDIT" \
  -H "Content-Type: application/json" \
  -d '{"tool_name": "get_audit_trail_tool", "arguments": {"session_id": "deploy-test"}}' \
  | python -m json.tool
```

Both should return valid JSON results. If either fails, stop and troubleshoot before proceeding.

### Step 6: Update Agent Runtime Environment Variables

For each agent on AgentCore Runtime, update environment variables:

```bash
# Values to set on each agent runtime
GATEWAY_URL=$GATEWAY_ENDPOINT
COGNITO_TOKEN_ENDPOINT=$COGNITO_TOKEN_ENDPOINT
COGNITO_CLIENT_ID=$COGNITO_APP_CLIENT_ID
COGNITO_CLIENT_SECRET=$COGNITO_APP_CLIENT_SECRET
ERP_DATA_SCOPE="disruptionai-gateway/erp-data"
AUDIT_SCOPE="disruptionai-gateway/audit"
```

Update via AgentCore API or console for all 4 agents:
- orchestrator_agent
- impact_assessment_agent
- capacity_optimization_agent
- constraint_matching_agent

### Step 7: End-to-End Validation

Test the full workflow through the WebSocket API:
1. Connect to `wss://x5u9j1d0p7.execute-api.us-east-1.amazonaws.com/prod`
2. Send a disruption scenario
3. Verify orchestrator invokes sub-agents
4. Verify sub-agents access ERP data through gateway (check Lambda CloudWatch logs)
5. Verify audit entries written through gateway

### Step 8: Decommission Old MCP Runtimes (Optional)

Once gateway is validated end-to-end, optionally remove old MCP server runtimes:

```bash
# Only after confirming gateway works
aws bedrock-agentcore delete-agent-runtime \
  --agent-runtime-id erp_data_mcp-XYsvQwFRom

aws bedrock-agentcore delete-agent-runtime \
  --agent-runtime-id audit_mcp-SHFeTx4uyE
```

## Rollback Plan

If gateway deployment fails at any step:

1. Agents still have old runtime URLs in their config until Step 6
2. If Step 6 is completed but gateway fails: Revert agent env vars to old runtime URLs
3. Old MCP runtimes remain active until explicitly deleted in Step 8
4. CDK stacks can be destroyed: `npx cdk destroy DisruptionAI-GatewayIam DisruptionAI-McpLambda DisruptionAI-Cognito`
5. Gateway can be deleted via: `aws bedrock-agentcore delete-gateway --gateway-id $GATEWAY_ID`

## Post-Deployment Monitoring

- Check Lambda CloudWatch logs for errors: `/aws/lambda/disruptionai-erp-data-mcp`, `/aws/lambda/disruptionai-audit-mcp`
- Check gateway access logs: `/aws/bedrock-agentcore/gateway/disruptionai-mcp-gateway`
- Monitor Cognito token request metrics in CloudWatch
- Verify agent response times are within acceptable range (gateway adds ~50-100ms latency)
