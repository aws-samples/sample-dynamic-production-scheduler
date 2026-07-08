"""Create erp-data-mcp Lambda target on AgentCore Gateway.

Based on the official AWS sample:
https://github.com/awslabs/amazon-bedrock-agentcore-samples/tree/main/02-use-cases/device-management-agent

Each tool's inputSchema includes an 'action_name' property so the gateway
passes it through to the Lambda event for routing (the gateway sends the
tool's arguments dict directly as the Lambda event payload).

Usage:
    python3 infrastructure/scripts/create_erp_data_target.py \
        --gateway-id <gateway-id> \
        --lambda-arn <erp-data-lambda-arn>
"""
import argparse
import logging
import sys

import boto3
from botocore.exceptions import ClientError

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

REGION = "us-east-1"
TARGET_NAME = "erp-data-mcp-target"
TARGET_DESCRIPTION = "ERP Data MCP tools — orders, capacity, materials, customers, tracker"


def _tool_schemas() -> list[dict]:
    """Return MCP tool definitions for all ERP data tools.

    Every tool includes 'action_name' as a required property so the
    gateway forwards it to the Lambda for dispatch routing.
    """
    return [
        {
            "name": "get_orders_tool",
            "description": "Query production orders by plant with optional status filter. use action_name default parameter value as 'get_orders_tool'",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "action_name": {"type": "string"},
                    "plant": {"type": "string", "description": "Plant name — 'Florida' or 'Ohio'."},
                    "status": {"type": "string", "description": "Optional status filter."},
                },
                "required": ["action_name", "plant"],
            },
        },
        {
            "name": "get_order_by_id_tool",
            "description": "Retrieve a single production order by its ID. use action_name default parameter value as 'get_order_by_id_tool'",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "action_name": {"type": "string"},
                    "order_id": {"type": "string", "description": "Order ID in format PO-YYYY-NNN."},
                },
                "required": ["action_name", "order_id"],
            },
        },
        {
            "name": "update_order_priority_tool",
            "description": "Update priority classification (P1/P2/P3) for a Florida order. use action_name default parameter value as 'update_order_priority_tool'",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "action_name": {"type": "string"},
                    "order_id": {"type": "string", "description": "Order ID in format PO-YYYY-NNN."},
                    "priority": {"type": "string", "description": "Priority level — 'P1', 'P2', or 'P3'."},
                },
                "required": ["action_name", "order_id", "priority"],
            },
        },
        {
            "name": "update_order_status_tool",
            "description": "Update order status (Active/Delayed/Transferred/Cancelled). use action_name default parameter value as 'update_order_status_tool'",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "action_name": {"type": "string"},
                    "order_id": {"type": "string", "description": "Order ID in format PO-YYYY-NNN."},
                    "status": {"type": "string", "description": "New status value."},
                },
                "required": ["action_name", "order_id", "status"],
            },
        },
        {
            "name": "get_machine_capacity_tool",
            "description": "Query machine capacity data for Ohio plant (Rolling Mill or Finishing Line). use action_name default parameter value as 'get_machine_capacity_tool'",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "action_name": {"type": "string"},
                    "machine_type": {"type": "string", "description": "Machine type — 'Rolling Mill' or 'Finishing Line'."},
                },
                "required": ["action_name", "machine_type"],
            },
        },
        {
            "name": "get_workforce_tool",
            "description": "Query Ohio plant workforce availability. use action_name default parameter value as 'get_workforce_tool'",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "action_name": {"type": "string"},
                },
                "required": ["action_name"],
            },
        },
        {
            "name": "get_materials_tool",
            "description": "Query raw material inventory at Ohio plant with optional material type filter. use action_name default parameter value as 'get_materials_tool'",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "action_name": {"type": "string"},
                    "material_type": {"type": "string", "description": "Optional material type filter."},
                },
                "required": ["action_name"],
            },
        },
        {
            "name": "get_customers_tool",
            "description": "Query customer data with optional customer ID filter. use action_name default parameter value as 'get_customers_tool'",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "action_name": {"type": "string"},
                    "customer_id": {"type": "string", "description": "Optional customer ID filter."},
                },
                "required": ["action_name"],
            },
        },
        {
            "name": "get_running_tracker_tool",
            "description": "Get current running capacity tracker for a workflow session. use action_name default parameter value as 'get_running_tracker_tool'",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "action_name": {"type": "string"},
                    "session_id": {"type": "string", "description": "Workflow session ID (UUID v4)."},
                },
                "required": ["action_name", "session_id"],
            },
        },
        {
            "name": "update_running_tracker_tool",
            "description": "Update running capacity tracker after a scheduling decision. use action_name default parameter value as 'update_running_tracker_tool'",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "action_name": {"type": "string"},
                    "session_id": {"type": "string", "description": "Workflow session ID (UUID v4)."},
                    "rolling_mill_normal_hrs": {"type": "number", "description": "Updated Rolling Mill normal surplus hours."},
                    "rolling_mill_overtime_hrs": {"type": "number", "description": "Updated Rolling Mill overtime hours."},
                    "rolling_mill_weekend_hrs": {"type": "number", "description": "Updated Rolling Mill weekend hours."},
                    "finishing_line_normal_hrs": {"type": "number", "description": "Updated Finishing Line normal surplus hours."},
                    "finishing_line_overtime_hrs": {"type": "number", "description": "Updated Finishing Line overtime hours."},
                    "finishing_line_weekend_hrs": {"type": "number", "description": "Updated Finishing Line weekend hours."},
                    "material_surplus_tons": {"type": "object", "description": "Updated material surplus map (material_type -> tons)."},
                    "workforce_surplus": {"type": "number", "description": "Updated workforce surplus count."},
                    "add_transferred": {"type": "string", "description": "Order ID to append to transferred list."},
                    "add_delayed": {"type": "string", "description": "Order ID to append to delayed list."},
                    "add_rejected": {"type": "string", "description": "Order ID to append to rejected list."},
                },
                "required": ["action_name", "session_id"],
            },
        },
    ]


def create_erp_data_target(gateway_id: str, lambda_arn: str) -> dict:
    """Create the erp-data-mcp Lambda target on the gateway."""
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
        description="Create erp-data-mcp Lambda target on AgentCore Gateway."
    )
    parser.add_argument("--gateway-id", required=True, help="AgentCore Gateway ID")
    parser.add_argument(
        "--lambda-arn", required=True,
        help="ARN of the erp-data-mcp Lambda function",
    )
    args = parser.parse_args()
    create_erp_data_target(args.gateway_id, args.lambda_arn)
