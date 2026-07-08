"""Create audit-mcp Lambda target on AgentCore Gateway.

Based on the official AWS sample:
https://github.com/awslabs/amazon-bedrock-agentcore-samples/tree/main/02-use-cases/device-management-agent

Each tool's inputSchema includes an 'action_name' property so the gateway
passes it through to the Lambda event for routing.

Usage:
    python3 infrastructure/scripts/create_audit_target.py \
        --gateway-id <gateway-id> \
        --lambda-arn <audit-lambda-arn>
"""
import argparse
import logging
import sys

import boto3
from botocore.exceptions import ClientError

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

REGION = "us-east-1"
TARGET_NAME = "audit-mcp-target"
TARGET_DESCRIPTION = "Audit MCP tools — write audit entries, read audit trail"


def _tool_schemas() -> list[dict]:
    """Return MCP tool definitions for the 2 audit tools.

    Every tool includes 'action_name' as a required property so the
    gateway forwards it to the Lambda for dispatch routing.
    """
    return [
        {
            "name": "write_audit_entry_tool",
            "description": "Write a decision or action to the audit trail. use action_name default parameter value as 'write_audit_entry_tool'",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "action_name": {"type": "string"},
                    "session_id": {"type": "string", "description": "Workflow session ID."},
                    "agent": {"type": "string", "description": "Name of the agent performing the action."},
                    "action": {"type": "string", "description": "Action being recorded."},
                    "details": {"type": "object", "description": "Structured details about the action."},
                    "timestamp": {"type": "string", "description": "ISO 8601 timestamp of the action."},
                },
                "required": ["action_name", "session_id", "agent", "action", "details", "timestamp"],
            },
        },
        {
            "name": "get_audit_trail_tool",
            "description": "Read audit entries for a session with optional agent and time filters. use action_name default parameter value as 'get_audit_trail_tool'",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "action_name": {"type": "string"},
                    "session_id": {"type": "string", "description": "Workflow session ID."},
                    "agent": {"type": "string", "description": "Optional agent name filter."},
                    "start_time": {"type": "string", "description": "Optional ISO 8601 start time filter."},
                },
                "required": ["action_name", "session_id"],
            },
        },
    ]


def create_audit_target(gateway_id: str, lambda_arn: str) -> dict:
    """Create the audit-mcp Lambda target on the gateway."""
    client = boto3.client("bedrock-agentcore-control", region_name=REGION)

    tools = _tool_schemas()
    logger.info(
        "Creating target '%s' with %d tool schemas on gateway %s ...",
        TARGET_NAME, len(tools), gateway_id,
    )

    lambda_target_config = {
        "mcp": {
            "lambda": {
                "lambdaArn": lambda_arn,
                "toolSchema": {
                    "inlinePayload": tools,
                },
            }
        }
    }

    credential_config = [
        {"credentialProviderType": "GATEWAY_IAM_ROLE"}
    ]

    try:
        response = client.create_gateway_target(
            gatewayIdentifier=gateway_id,
            name=TARGET_NAME,
            description=TARGET_DESCRIPTION,
            credentialProviderConfigurations=credential_config,
            targetConfiguration=lambda_target_config,
        )
    except ClientError as exc:
        logger.error("Failed to create target: %s", exc)
        sys.exit(1)

    target_id = response.get("targetId")
    logger.info("Target created successfully.")
    logger.info("  Target ID : %s", target_id)
    logger.info("  Lambda    : %s", lambda_arn)

    return {"target_id": target_id}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Create audit-mcp Lambda target on AgentCore Gateway."
    )
    parser.add_argument("--gateway-id", required=True, help="AgentCore Gateway ID")
    parser.add_argument(
        "--lambda-arn", required=True,
        help="ARN of the audit-mcp Lambda function",
    )
    args = parser.parse_args()
    create_audit_target(args.gateway_id, args.lambda_arn)
