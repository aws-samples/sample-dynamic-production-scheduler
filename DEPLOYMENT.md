# DisruptionAI — Deployment Guide

> **⚠️ Important:** This deployment guide is for a sample/demo application. The infrastructure patterns, IAM policies, and configurations described here are **not intended for production use** without thorough security review and hardening. Do not deploy to production accounts without proper security assessment.

Everything is Infrastructure as Code. A single `cdk deploy --all` deploys the entire platform — agents, gateway, frontend, and all supporting infrastructure — to any AWS account.

## Prerequisites

| Tool | Version | Install |
|------|---------|---------|
| AWS CLI v2 | Latest | `brew install awscli` or [AWS docs](https://docs.aws.amazon.com/cli/latest/userguide/getting-started-install.html) |
| Node.js | 22+ | `brew install node` or [nodejs.org](https://nodejs.org) |
| Python | 3.13+ | `brew install python@3.13` or [python.org](https://python.org) |
| npm | 9+ | Comes with Node.js |
| pip | Latest | Comes with Python |

AWS account requirements:
- Region: `us-east-1`
- Bedrock AgentCore access enabled
- Admin-level IAM credentials configured
- `iam:CreateServiceLinkedRole` permission (for AgentCore service-linked roles)

```bash
aws configure
# Region: us-east-1
aws sts get-caller-identity  # verify access
```

---

## Quick Deploy (One Command)

```bash
chmod +x deploy.sh
./deploy.sh
```

This script handles everything: CDK bootstrap, Lambda bundling, stack deployment, DynamoDB seeding, and frontend build/deploy. Skip to the Verification section when it completes.

---

## Manual Deploy (Step by Step)

### Step 1: Bundle MCP Lambda Dependencies

```bash
# ERP Data MCP
cd erp-data-mcp
mkdir -p .lambda-bundle
pip install --target .lambda-bundle --platform manylinux2014_x86_64 --only-binary=:all: -r requirements.txt
cp -r src/* .lambda-bundle/
cd ..

# Audit MCP
cd audit-mcp
mkdir -p .lambda-bundle
pip install --target .lambda-bundle --platform manylinux2014_x86_64 --only-binary=:all: -r requirements.txt
cp -r src/* .lambda-bundle/
cd ..
```

### Step 2: Deploy All CDK Stacks

```bash
cd infrastructure
npm install
npx cdk bootstrap  # first time only
npx cdk deploy --all --require-approval never --outputs-file cdk-outputs.json
```

This deploys 11 stacks in dependency order:

| Stack | What It Creates |
|-------|-----------------|
| DisruptionAI-Database | DynamoDB tables (orders, capacity, workforce, materials, customers, transfers, workflow-state, tracker, audit) |
| DisruptionAI-Monitoring | CloudWatch log groups |
| DisruptionAI-IAM | Lambda execution roles and policies |
| DisruptionAI-WebSocket | WebSocket API Gateway |
| DisruptionAI-Cognito | User Pool + Identity Pool (frontend auth) |
| DisruptionAI-McpLambda | ERP Data + Audit Lambda functions |
| DisruptionAI-GatewayIam | Gateway management IAM role |
| DisruptionAI-Gateway | MCP Gateway + Cognito M2M auth + Lambda targets (13 tools) |
| DisruptionAI-AgentCore | 4 agent runtimes + 4 memory resources |
| DisruptionAI-RestProxy | Lambda Function URL (Python 3.13, AWS_IAM auth) |
| DisruptionAI-Frontend | S3 bucket + CloudFront distribution |

Key stacks explained:

- **DisruptionAI-Gateway**: Creates the AgentCore MCP Gateway with auto-provisioned Cognito M2M authentication. Adds two Lambda targets (ERP Data with 11 tools, Audit with 2 tools) with inline tool schemas. No manual gateway setup scripts needed.

- **DisruptionAI-AgentCore**: Deploys all 4 agent runtimes using `AgentRuntimeArtifact.fromCodeAsset()` — packages agent code directly from the repo, no Docker or `agentcore` CLI required. Creates Memory resources for each agent. Wires sub-agent ARNs into the orchestrator automatically. Grants cross-agent invoke, Bedrock model, and Gateway permissions.

### Step 3: Seed DynamoDB

```bash
cd erp-data-mcp
python3 -m venv .venv
source .venv/bin/activate
pip install -e .
erp-data-mcp-seed
```

### Step 4: Build and Deploy Frontend

Update `frontend-spa/public/config.json` with values from CDK outputs:

```json
{
  "VITE_API_URL": "<RestProxyUrl from cdk-outputs.json>",
  "VITE_USER_POOL_ID": "<UserPoolId>",
  "VITE_USER_CLIENT_ID": "<UserAppClientId>",
  "VITE_IDENTITY_POOL_ID": "<IdentityPoolId>",
  "VITE_AWS_REGION": "us-east-1"
}
```

Build and deploy:

```bash
cd frontend-spa
npm install
npm run build

ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
aws s3 sync dist/ s3://disruptionai-frontend-${ACCOUNT_ID} --delete

DIST_ID=$(aws cloudfront list-distributions \
  --query "DistributionList.Items[?Origins.Items[?contains(DomainName,'disruptionai-frontend')]].Id | [0]" \
  --output text)
aws cloudfront create-invalidation --distribution-id $DIST_ID --paths "/*"
```

---

## Verification

1. Open the CloudFront URL (from CDK outputs)
2. Sign up with your email (Cognito sends a verification code)
3. Confirm and sign in
4. Type: "Florida plant is shutting down due to a hurricane. Assess the impact on all active orders."
5. The orchestrator invokes sub-agents and returns a structured disruption response

---

## CDK Stack Architecture

```
Database ──┐
Monitoring ─┤
            ├── IAM
            ├── WebSocket
            ├── Cognito
            ├── McpLambda ──┬── GatewayIam
            │               └── Gateway (MCP Gateway + Cognito M2M + Lambda targets)
            │
            ├── AgentCore (4 runtimes + 4 memory, wired to Gateway)
            ├── RestProxy (Lambda Function URL)
            └── Frontend (S3 + CloudFront)
```

---

## CI/CD (GitLab)

For ongoing development, the GitLab pipeline automates builds and deploys on merge to `main`:

```
build:frontend + build:mcp-lambdas (parallel, on MRs + main)
  └── deploy:infrastructure (cdk deploy --all)
        └── deploy:agents:* (4 parallel agentcore deploys)
              └── deploy:frontend (S3 sync + CloudFront invalidation)
```

---

## Troubleshooting

### CDK deploy fails with "Layer version does not exist"
The REST proxy uses Python 3.13 runtime with built-in boto3. Do not add custom Lambda layers.

### CDK deploy fails with UPDATE_ROLLBACK_COMPLETE
The stack is in a failed state. Fix the root cause and re-run, or delete the stack in the AWS Console.

### Agent deploy fails with ThrottlingException
AWS CodeBuild API rate limiting. The pipeline has auto-retry configured. Re-run the pipeline.

### "User is not confirmed" on sign-in
Check email for the Cognito verification code.

### Lambda Function URL returns 403
Cognito Identity Pool authenticated role needs both `lambda:InvokeFunctionUrl` and `lambda:InvokeFunction`. The CDK stack grants both automatically.

### Duplicate CORS headers causing browser rejection
The Lambda Function URL handles CORS. Do not set `Access-Control-Allow-Origin` in the Lambda handler response.

### Gateway returns 401/403
The Gateway stack auto-creates Cognito M2M auth. Verify the agents have the correct `COGNITO_TOKEN_ENDPOINT` and `COGNITO_CLIENT_ID` environment variables (set automatically by CDK).
