# Build Instructions — Gateway Rework (Rework Cycle 2)

## Prerequisites

- **Node.js**: >= 18.x (for CDK)
- **Python**: >= 3.11 (for Lambda handlers and gateway scripts)
- **AWS CDK CLI**: 2.178.0 (`npm install -g aws-cdk@2.178.0`)
- **AWS CLI**: v2 (configured with credentials for account `058264253938`, region `us-east-1`)
- **pip**: Latest (for Python package installation)
- **boto3**: >= 1.34.0 (for gateway setup scripts)

## Environment Variables

```bash
export CDK_DEFAULT_ACCOUNT=058264253938
export CDK_DEFAULT_REGION=us-east-1
export AWS_REGION=us-east-1
```

## Phase 1: CDK Infrastructure Build and Deploy

### 1.1 Install CDK Dependencies

```bash
cd infrastructure
npm install
```

### 1.2 Build TypeScript

```bash
npm run build
```

Expected output: No compilation errors. TypeScript compiles all stacks including new `cognito-stack.ts`, `mcp-lambda-stack.ts`, and `gateway-iam-stack.ts`.

### 1.3 Run CDK Synth (Validation)

```bash
npx cdk synth
```

Expected output: CloudFormation templates generated for all stacks including:
- `DisruptionAI-Cognito`
- `DisruptionAI-McpLambda`
- `DisruptionAI-GatewayIam`

### 1.4 Deploy New Stacks

Deploy in dependency order:

```bash
# Step 1: Cognito stack (no dependencies on new stacks)
npx cdk deploy DisruptionAI-Cognito --require-approval never

# Step 2: MCP Lambda stack (depends on Database stack for table ARNs)
npx cdk deploy DisruptionAI-McpLambda --require-approval never

# Step 3: Gateway IAM stack (depends on Cognito + McpLambda outputs)
npx cdk deploy DisruptionAI-GatewayIam --require-approval never

# Step 4: Update IAM stack (adds gateway invoke to ECS task role)
npx cdk deploy DisruptionAI-IAM --require-approval never
```

### 1.5 Capture Stack Outputs

After deployment, note these outputs:
- `DisruptionAI-Cognito.UserPoolId` -> `COGNITO_USER_POOL_ID`
- `DisruptionAI-Cognito.AppClientId` -> `COGNITO_APP_CLIENT_ID`
- `DisruptionAI-Cognito.TokenEndpoint` -> `COGNITO_TOKEN_ENDPOINT`
- `DisruptionAI-McpLambda.ErpDataLambdaArn` -> `ERP_DATA_LAMBDA_ARN`
- `DisruptionAI-McpLambda.AuditLambdaArn` -> `AUDIT_LAMBDA_ARN`

## Phase 2: Retrieve Cognito App Client Secret

The App Client secret is not exposed as a CDK output. Retrieve it via CLI:

```bash
aws cognito-idp describe-user-pool-client \
  --user-pool-id $COGNITO_USER_POOL_ID \
  --client-id $COGNITO_APP_CLIENT_ID \
  --query 'UserPoolClient.ClientSecret' \
  --output text
```

Store as `COGNITO_APP_CLIENT_SECRET`.

## Phase 3: Gateway Setup Scripts

Run scripts in order (each depends on the previous):

### 3.1 Create Gateway

```bash
python infrastructure/scripts/create_gateway.py \
  --cognito-user-pool-id $COGNITO_USER_POOL_ID \
  --cognito-app-client-id $COGNITO_APP_CLIENT_ID
```

Expected output: Gateway ID and endpoint URL. Config saved to `infrastructure/scripts/.gateway-config.json`.

Store the gateway ID as `GATEWAY_ID` and endpoint as `GATEWAY_ENDPOINT`.

### 3.2 Create ERP Data Target

```bash
python infrastructure/scripts/create_erp_data_target.py \
  --gateway-id $GATEWAY_ID \
  --lambda-arn $ERP_DATA_LAMBDA_ARN
```

Expected output: Target ID for erp-data-mcp with 10 tool schemas registered.

### 3.3 Create Audit Target

```bash
python infrastructure/scripts/create_audit_target.py \
  --gateway-id $GATEWAY_ID \
  --lambda-arn $AUDIT_LAMBDA_ARN
```

Expected output: Target ID for audit-mcp with 2 tool schemas registered.

### 3.4 Enable Gateway Observability

```bash
python infrastructure/scripts/gateway_observability.py \
  --gateway-id $GATEWAY_ID
```

Expected output: CloudWatch log group created with 90-day retention, gateway logging enabled.

### 3.5 Register Credential Providers

```bash
python infrastructure/scripts/cognito_credentials_provider.py \
  --cognito-user-pool-id $COGNITO_USER_POOL_ID \
  --cognito-app-client-id $COGNITO_APP_CLIENT_ID \
  --cognito-app-client-secret $COGNITO_APP_CLIENT_SECRET
```

Expected output: 4 OAuth2 credential providers registered (orchestrator, impact-assessment, capacity-optimization, constraint-matching).

## Phase 4: Update Cross-Agent Permissions

```bash
bash infrastructure/scripts/apply-cross-agent-permissions.sh
```

Expected output: All `AmazonBedrockAgentCoreSDKRuntime-*` roles updated with both `InvokeAgentRuntime` and `InvokeGateway` permissions.

## Phase 5: Configure Agent Environment Variables

Update each agent's environment with gateway configuration:

```bash
export GATEWAY_URL=$GATEWAY_ENDPOINT
export COGNITO_TOKEN_ENDPOINT=$COGNITO_TOKEN_ENDPOINT
export COGNITO_CLIENT_ID=$COGNITO_APP_CLIENT_ID
export COGNITO_CLIENT_SECRET=$COGNITO_APP_CLIENT_SECRET
export ERP_DATA_SCOPE="disruptionai-gateway/erp-data"
export AUDIT_SCOPE="disruptionai-gateway/audit"
```

For AgentCore Runtime agents, update the runtime environment variables via the AgentCore API or console.

## Troubleshooting

### CDK Deploy Fails on Cognito Stack
- **Cause**: Domain prefix conflict (must be globally unique)
- **Fix**: The domain uses `disruptionai-gateway-{ACCOUNT_ID}` which should be unique. If conflict, modify `cognito-stack.ts` domain prefix.

### Lambda Deploy Fails — Missing Dependencies
- **Cause**: Lambda code asset doesn't include dependencies
- **Fix**: Ensure `erp-data-mcp/src/` and `audit-mcp/src/` contain all required packages. Consider using Lambda layers or bundling dependencies.

### Gateway Script Fails — Access Denied
- **Cause**: IAM role not yet deployed or assumed
- **Fix**: Ensure `DisruptionAI-GatewayIam` stack is deployed and you have `sts:AssumeRole` on the gateway management role.

### Agent Cannot Authenticate to Gateway
- **Cause**: Cognito token endpoint or credentials misconfigured
- **Fix**: Verify `COGNITO_TOKEN_ENDPOINT`, `COGNITO_CLIENT_ID`, `COGNITO_CLIENT_SECRET` are correct. Test token retrieval manually:

```bash
curl -X POST $COGNITO_TOKEN_ENDPOINT \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "grant_type=client_credentials&client_id=$COGNITO_APP_CLIENT_ID&client_secret=$COGNITO_APP_CLIENT_SECRET&scope=disruptionai-gateway/erp-data"
```
