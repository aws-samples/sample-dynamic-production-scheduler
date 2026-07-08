#!/usr/bin/env bash
# ---------------------------------------------------------------------------
# apply-cross-agent-permissions.sh
#
# Discovers all IAM roles matching AmazonBedrockAgentCoreSDKRuntime-* and
# attaches an inline policy granting bedrock-agentcore:InvokeAgentRuntime
# on all AgentCore runtimes and bedrock-agentcore:InvokeGateway on all
# AgentCore gateways in the target account.
#
# Usage:
#   ./infrastructure/scripts/apply-cross-agent-permissions.sh
#
# Prerequisites:
#   - AWS CLI v2 configured with credentials that can iam:ListRoles and
#     iam:PutRolePolicy on the target account.
# ---------------------------------------------------------------------------
set -euo pipefail

ACCOUNT_ID="${ACCOUNT_ID:?Set ACCOUNT_ID env var}"
REGION="us-east-1"
POLICY_NAME="CrossAgentInvoke"

POLICY_DOCUMENT=$(cat <<EOF
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "AgentCoreCrossInvoke",
      "Effect": "Allow",
      "Action": "bedrock-agentcore:InvokeAgentRuntime",
      "Resource": "arn:aws:bedrock-agentcore:${REGION}:${ACCOUNT_ID}:runtime/orchestrator_agent-*"
    },
    {
      "Sid": "AgentCoreSubAgentInvoke",
      "Effect": "Allow",
      "Action": "bedrock-agentcore:InvokeAgentRuntime",
      "Resource": [
        "arn:aws:bedrock-agentcore:${REGION}:${ACCOUNT_ID}:runtime/impact_assessment_agent-*",
        "arn:aws:bedrock-agentcore:${REGION}:${ACCOUNT_ID}:runtime/capacity_optimization_agent-*",
        "arn:aws:bedrock-agentcore:${REGION}:${ACCOUNT_ID}:runtime/constraint_matching_agent-*"
      ]
    },
    {
      "Sid": "AgentCoreGatewayInvoke",
      "Effect": "Allow",
      "Action": "bedrock-agentcore:InvokeGateway",
      "Resource": "arn:aws:bedrock-agentcore:${REGION}:${ACCOUNT_ID}:gateway/disruptionai-*"
    },
    {
      "Sid": "AgentCoreMemory",
      "Effect": "Allow",
      "Action": [
        "bedrock-agentcore:GetMemory",
        "bedrock-agentcore:CreateMemoryEvent",
        "bedrock-agentcore:SearchMemoryEvents"
      ],
      "Resource": "arn:aws:bedrock-agentcore:${REGION}:${ACCOUNT_ID}:memory/*"
    }
  ]
}
EOF
)

echo "Discovering AgentCore execution roles..."

ROLE_NAMES=$(aws iam list-roles \
  --query "Roles[?starts_with(RoleName, 'AmazonBedrockAgentCoreSDKRuntime-')].RoleName" \
  --output text)

if [ -z "${ROLE_NAMES}" ]; then
  echo "No AmazonBedrockAgentCoreSDKRuntime-* roles found. Nothing to do."
  exit 0
fi

UPDATED=0
for ROLE_NAME in ${ROLE_NAMES}; do
  echo "  Attaching ${POLICY_NAME} to ${ROLE_NAME} ..."
  aws iam put-role-policy \
    --role-name "${ROLE_NAME}" \
    --policy-name "${POLICY_NAME}" \
    --policy-document "${POLICY_DOCUMENT}"
  UPDATED=$((UPDATED + 1))
done

echo "Done. Updated ${UPDATED} role(s)."
