#!/usr/bin/env bash
# =============================================================================
# DisruptionAI — One-Command Deployment Script
# =============================================================================
# Deploys the entire DisruptionAI platform to a fresh AWS account.
#
# Prerequisites:
#   - AWS CLI v2 configured with admin credentials (us-east-1)
#   - Node.js 22+
#   - Python 3.13+ (or 3.11+)
#   - pip
#   - npm
#
# Usage:
#   chmod +x deploy.sh
#   ./deploy.sh
#
# The script will:
#   1. Deploy CDK infrastructure (9 stacks)
#   2. Seed DynamoDB with demo data
#   3. Deploy 4 Bedrock AgentCore agents
#   4. Build and deploy the frontend
#   5. Print the application URL
# =============================================================================

set -euo pipefail

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

log()  { echo -e "${GREEN}[✓]${NC} $1"; }
warn() { echo -e "${YELLOW}[!]${NC} $1"; }
fail() { echo -e "${RED}[✗]${NC} $1"; exit 1; }

# ---------------------------------------------------------------------------
# 0. Preflight checks
# ---------------------------------------------------------------------------
echo ""
echo "=========================================="
echo "  DisruptionAI — Full Deployment"
echo "=========================================="
echo ""

command -v aws   >/dev/null 2>&1 || fail "AWS CLI not found. Install: https://docs.aws.amazon.com/cli/latest/userguide/getting-started-install.html"
command -v node  >/dev/null 2>&1 || fail "Node.js not found. Install: https://nodejs.org"
command -v npm   >/dev/null 2>&1 || fail "npm not found. Install with Node.js"
command -v python3 >/dev/null 2>&1 || fail "Python 3 not found. Install: https://python.org"
command -v pip3  >/dev/null 2>&1 || warn "pip3 not found, will try pip"

ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text 2>/dev/null) || fail "AWS credentials not configured. Run: aws configure"
REGION=${AWS_DEFAULT_REGION:-us-east-1}

log "AWS Account: $ACCOUNT_ID"
log "Region: $REGION"
log "Node: $(node --version)"
log "Python: $(python3 --version)"
echo ""

# ---------------------------------------------------------------------------
# 1. Deploy CDK Infrastructure
# ---------------------------------------------------------------------------
echo "=========================================="
echo "  Step 1: CDK Infrastructure"
echo "=========================================="

# Bundle MCP Lambda dependencies
log "Bundling ERP Data MCP Lambda..."
(
  cd erp-data-mcp
  rm -rf .lambda-bundle
  mkdir -p .lambda-bundle
  pip3 install --quiet --target .lambda-bundle --platform manylinux2014_x86_64 --only-binary=:all: -r requirements.txt 2>/dev/null || \
    python3 -m pip install --quiet --target .lambda-bundle --platform manylinux2014_x86_64 --only-binary=:all: -r requirements.txt
  cp -r src/* .lambda-bundle/
)
log "ERP Data MCP bundled"

log "Bundling Audit MCP Lambda..."
(
  cd audit-mcp
  rm -rf .lambda-bundle
  mkdir -p .lambda-bundle
  pip3 install --quiet --target .lambda-bundle --platform manylinux2014_x86_64 --only-binary=:all: -r requirements.txt 2>/dev/null || \
    python3 -m pip install --quiet --target .lambda-bundle --platform manylinux2014_x86_64 --only-binary=:all: -r requirements.txt
  cp -r src/* .lambda-bundle/
)
log "Audit MCP bundled"

# Install CDK dependencies and deploy
log "Installing CDK dependencies..."
(cd infrastructure && npm ci --silent)

log "Bootstrapping CDK (if needed)..."
(cd infrastructure && npx cdk bootstrap aws://$ACCOUNT_ID/$REGION 2>/dev/null || true)

log "Deploying all CDK stacks..."
(cd infrastructure && npx cdk deploy --all --require-approval never --outputs-file cdk-outputs.json)
log "CDK deployment complete"

# Extract outputs
CDK_OUTPUTS="infrastructure/cdk-outputs.json"
if [ ! -f "$CDK_OUTPUTS" ]; then
  fail "CDK outputs file not found. Check deployment logs."
fi

# Parse CDK outputs
REST_PROXY_URL=$(python3 -c "
import json
with open('$CDK_OUTPUTS') as f:
    outputs = json.load(f)
for stack in outputs.values():
    for k, v in stack.items():
        if 'RestProxyUrl' in k:
            print(v)
            break
" 2>/dev/null || echo "")

USER_POOL_ID=$(python3 -c "
import json
with open('$CDK_OUTPUTS') as f:
    outputs = json.load(f)
for stack in outputs.values():
    for k, v in stack.items():
        if 'UserPoolId' in k:
            print(v)
            break
" 2>/dev/null || echo "")

USER_CLIENT_ID=$(python3 -c "
import json
with open('$CDK_OUTPUTS') as f:
    outputs = json.load(f)
for stack in outputs.values():
    for k, v in stack.items():
        if 'UserAppClientId' in k or 'UserClientId' in k:
            print(v)
            break
" 2>/dev/null || echo "")

IDENTITY_POOL_ID=$(python3 -c "
import json
with open('$CDK_OUTPUTS') as f:
    outputs = json.load(f)
for stack in outputs.values():
    for k, v in stack.items():
        if 'IdentityPoolId' in k:
            print(v)
            break
" 2>/dev/null || echo "")

DISTRIBUTION_URL=$(python3 -c "
import json
with open('$CDK_OUTPUTS') as f:
    outputs = json.load(f)
for stack in outputs.values():
    for k, v in stack.items():
        if 'DistributionUrl' in k:
            print(v)
            break
" 2>/dev/null || echo "")

log "REST Proxy URL: $REST_PROXY_URL"
log "User Pool ID: $USER_POOL_ID"
log "User Client ID: $USER_CLIENT_ID"
log "Identity Pool ID: $IDENTITY_POOL_ID"
echo ""

# ---------------------------------------------------------------------------
# 2. Seed DynamoDB
# ---------------------------------------------------------------------------
echo "=========================================="
echo "  Step 2: Seed DynamoDB Tables"
echo "=========================================="

log "Installing ERP Data MCP package..."
(
  cd erp-data-mcp
  python3 -m venv .venv-seed 2>/dev/null || true
  .venv-seed/bin/pip install --quiet -e . 2>/dev/null || pip3 install --quiet -e .
  .venv-seed/bin/erp-data-mcp-seed 2>/dev/null || python3 -c "from erp_data_mcp.seed.loader import seed_all; seed_all()" 2>/dev/null || warn "Seed command not found, skipping (tables may need manual seeding)"
)
log "DynamoDB seeded"
echo ""

# ---------------------------------------------------------------------------
# 3. Deploy Bedrock AgentCore Agents
# ---------------------------------------------------------------------------
echo "=========================================="
echo "  Step 3: Deploy AgentCore Agents"
echo "=========================================="

pip3 install --quiet bedrock-agentcore-starter-toolkit 2>/dev/null || python3 -m pip install --quiet bedrock-agentcore-starter-toolkit

AGENTS=("orchestrator-agent" "impact-assessment-agent" "capacity-optimization-agent" "constraint-matching-agent")
ENTRYPOINTS=(
  "src/orchestrator_agent/agent.py"
  "src/impact_assessment_agent/agent.py"
  "src/capacity_optimization_agent/agent.py"
  "src/constraint_matching_agent/agent.py"
)

for i in "${!AGENTS[@]}"; do
  AGENT_DIR="${AGENTS[$i]}"
  ENTRYPOINT="${ENTRYPOINTS[$i]}"
  log "Deploying $AGENT_DIR..."
  (
    cd "$AGENT_DIR"
    agentcore configure --entrypoint "$ENTRYPOINT" --non-interactive 2>&1 | tail -3
    agentcore deploy --auto-update-on-conflict 2>&1 | tail -5
  ) || warn "$AGENT_DIR deploy failed — may need manual retry"
  echo ""
done

log "Agent deployment initiated (CodeBuild builds may take a few minutes)"
echo ""

# ---------------------------------------------------------------------------
# 4. Build and Deploy Frontend
# ---------------------------------------------------------------------------
echo "=========================================="
echo "  Step 4: Build & Deploy Frontend"
echo "=========================================="

# Update frontend config with CDK outputs
log "Updating frontend configuration..."
cat > frontend-spa/public/config.json << EOF
{
  "VITE_API_URL": "${REST_PROXY_URL}",
  "VITE_USER_POOL_ID": "${USER_POOL_ID}",
  "VITE_USER_CLIENT_ID": "${USER_CLIENT_ID}",
  "VITE_IDENTITY_POOL_ID": "${IDENTITY_POOL_ID}",
  "VITE_AWS_REGION": "${REGION}"
}
EOF

cat > frontend-spa/.env << EOF
VITE_API_URL=${REST_PROXY_URL}
VITE_USER_POOL_ID=${USER_POOL_ID}
VITE_USER_CLIENT_ID=${USER_CLIENT_ID}
VITE_IDENTITY_POOL_ID=${IDENTITY_POOL_ID}
VITE_AWS_REGION=${REGION}
EOF

log "Building frontend..."
(cd frontend-spa && npm ci --silent && npm run build --silent)
log "Frontend built"

BUCKET_NAME="disruptionai-frontend-${ACCOUNT_ID}"
log "Deploying to S3: $BUCKET_NAME"
aws s3 sync frontend-spa/dist/ "s3://${BUCKET_NAME}/" --delete --quiet

# Invalidate CloudFront
DISTRIBUTION_ID=$(aws cloudfront list-distributions \
  --query "DistributionList.Items[?Origins.Items[?contains(DomainName, '${BUCKET_NAME}')]].Id | [0]" \
  --output text 2>/dev/null || echo "")

if [ -n "$DISTRIBUTION_ID" ] && [ "$DISTRIBUTION_ID" != "None" ]; then
  log "Invalidating CloudFront: $DISTRIBUTION_ID"
  aws cloudfront create-invalidation --distribution-id "$DISTRIBUTION_ID" --paths "/*" --output text >/dev/null
fi

echo ""

# ---------------------------------------------------------------------------
# 5. Done
# ---------------------------------------------------------------------------
echo "=========================================="
echo "  Deployment Complete"
echo "=========================================="
echo ""
log "Application URL: ${DISTRIBUTION_URL}"
log "REST Proxy: ${REST_PROXY_URL}"
echo ""
echo "To sign in:"
echo "  1. Open ${DISTRIBUTION_URL}"
echo "  2. Click 'Sign Up' and register with your email"
echo "  3. Check email for verification code"
echo "  4. Sign in and start a disruption scenario"
echo ""
echo "Example prompt:"
echo "  'Florida plant is shutting down due to a hurricane."
echo "   Assess the impact on all active orders.'"
echo ""
