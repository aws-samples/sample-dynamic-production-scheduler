#!/usr/bin/env python3
"""Update both gateway targets to include action_name in toolSchema.

This follows the AWS reference pattern from device-management-agent where
each tool's inputSchema includes an 'action_name' property that the gateway
passes through to the Lambda event for dispatch routing.
"""
import json
import os
import boto3

REGION = "us-east-1"
GATEWAY_ID = "disruptionai-mcp-gateway-p9qpkebcdw"
ERP_TARGET_ID = "JMPLQMMNLY"
AUDIT_TARGET_ID = "KMLDC9NLB4"
ERP_LAMBDA_ARN = os.environ.get("ERP_LAMBDA_ARN", "arn:aws:lambda:us-east-1:ACCOUNT_ID:function:disruptionai-erp-data-mcp")
AUDIT_LAMBDA_ARN = os.environ.get("AUDIT_LAMBDA_ARN", "arn:aws:lambda:us-east-1:ACCOUNT_ID:function:disruptionai-audit-mcp")

client = boto3.client("bedrock-agentcore-control", region_name=REGION)


def erp_tool_schemas():
    return [
        {
            "name": "get_orders_tool",
            "description": "Query production orders by plant with optional status filter. use action_name default parameter value as 'get_orders_tool'",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "action_name": {"type": "string"},
                    "plant": {"type": "string", "description": "Plant name"},
                    "status": {"type": "string", "description": "Optional status filter"},
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
                    "order_id": {"type": "string", "description": "Order ID"},
                },
                "required": ["action_name", "order_id"],
            },
        },
        {
            "name": "update_order_priority_tool",
            "description": "Update priority classification for a Florida order. use action_name default parameter value as 'update_order_priority_tool'",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "action_name": {"type": "string"},
                    "order_id": {"type": "string", "description": "Order ID"},
                    "priority": {"type": "string", "description": "P1, P2, or P3"},
                },
                "required": ["action_name", "order_id", "priority"],
            },
        },
        {
            "name": "update_order_status_tool",
            "description": "Update order status. use action_name default parameter value as 'update_order_status_tool'",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "action_name": {"type": "string"},
                    "order_id": {"type": "string", "description": "Order ID"},
                    "status": {"type": "string", "description": "New status"},
                },
                "required": ["action_name", "order_id", "status"],
            },
        },
        {
            "name": "get_machine_capacity_tool",
            "description": "Query machine capacity data for Ohio plant. use action_name default parameter value as 'get_machine_capacity_tool'",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "action_name": {"type": "string"},
                    "machine_type": {"type": "string", "description": "Rolling Mill or Finishing Line"},
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
            "description": "Query raw material inventory at Ohio plant. use action_name default parameter value as 'get_materials_tool'",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "action_name": {"type": "string"},
                    "material_type": {"type": "string", "description": "Optional material type filter"},
                },
                "required": ["action_name"],
            },
        },
        {
            "name": "get_customers_tool",
            "description": "Query customer data. use action_name default parameter value as 'get_customers_tool'",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "action_name": {"type": "string"},
                    "customer_id": {"type": "string", "description": "Optional customer ID filter"},
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
                    "session_id": {"type": "string", "description": "Workflow session ID"},
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
                    "session_id": {"type": "string", "description": "Workflow session ID"},
                    "rolling_mill_normal_hrs": {"type": "number"},
                    "rolling_mill_overtime_hrs": {"type": "number"},
                    "rolling_mill_weekend_hrs": {"type": "number"},
                    "finishing_line_normal_hrs": {"type": "number"},
                    "finishing_line_overtime_hrs": {"type": "number"},
                    "finishing_line_weekend_hrs": {"type": "number"},
                    "material_surplus_tons": {"type": "object"},
                    "workforce_surplus": {"type": "number"},
                    "add_transferred": {"type": "string"},
                    "add_delayed": {"type": "string"},
                    "add_rejected": {"type": "string"},
                },
                "required": ["action_name", "session_id"],
            },
        },
        {
            "name": "reset_seed_data_tool",
            "description": "Reset all ERP data to a fresh seed state. Use 'demo' mode for a curated 16-order subset (faster demos) or 'full' for all 40 orders. use action_name default parameter value as 'reset_seed_data_tool'",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "action_name": {"type": "string"},
                    "mode": {"type": "string", "description": "Seed mode: 'demo' or 'full'"},
                },
                "required": ["action_name", "mode"],
            },
        },
    ]


def audit_tool_schemas():
    return [
        {
            "name": "write_audit_entry_tool",
            "description": "Write a decision or action to the audit trail. use action_name default parameter value as 'write_audit_entry_tool'",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "action_name": {"type": "string"},
                    "session_id": {"type": "string", "description": "Workflow session ID"},
                    "agent": {"type": "string", "description": "Agent name"},
                    "action": {"type": "string", "description": "Action being recorded"},
                    "details": {"type": "object", "description": "Structured details"},
                    "timestamp": {"type": "string", "description": "ISO 8601 timestamp"},
                },
                "required": ["action_name", "session_id", "agent", "action", "details", "timestamp"],
            },
        },
        {
            "name": "get_audit_trail_tool",
            "description": "Read audit entries for a session. use action_name default parameter value as 'get_audit_trail_tool'",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "action_name": {"type": "string"},
                    "session_id": {"type": "string", "description": "Workflow session ID"},
                    "agent": {"type": "string", "description": "Optional agent name filter"},
                    "start_time": {"type": "string", "description": "Optional ISO 8601 start time"},
                },
                "required": ["action_name", "session_id"],
            },
        },
    ]


CRED_CONFIG = [{"credentialProviderType": "GATEWAY_IAM_ROLE"}]

# --- Update ERP target ---
print("Updating ERP data target (JMPLQMMNLY) ...")
erp_resp = client.update_gateway_target(
    gatewayIdentifier=GATEWAY_ID,
    targetId=ERP_TARGET_ID,
    name="erp-data-mcp-target",
    description="ERP Data MCP tools with action_name routing",
    credentialProviderConfigurations=CRED_CONFIG,
    targetConfiguration={
        "mcp": {
            "lambda": {
                "lambdaArn": ERP_LAMBDA_ARN,
                "toolSchema": {"inlinePayload": erp_tool_schemas()},
            }
        }
    },
)
print(f"  ERP target updated: status={erp_resp.get('status')}")

# --- Update Audit target ---
print("Updating Audit target (KMLDC9NLB4) ...")
audit_resp = client.update_gateway_target(
    gatewayIdentifier=GATEWAY_ID,
    targetId=AUDIT_TARGET_ID,
    name="audit-mcp-target",
    description="Audit MCP tools with action_name routing",
    credentialProviderConfigurations=CRED_CONFIG,
    targetConfiguration={
        "mcp": {
            "lambda": {
                "lambdaArn": AUDIT_LAMBDA_ARN,
                "toolSchema": {"inlinePayload": audit_tool_schemas()},
            }
        }
    },
)
print(f"  Audit target updated: status={audit_resp.get('status')}")

print("\nDone. Both targets updated with action_name in toolSchema.")
