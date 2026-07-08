import * as cdk from "aws-cdk-lib";
import * as lambda from "aws-cdk-lib/aws-lambda";
import * as agentcore from "@aws-cdk/aws-bedrock-agentcore-alpha";
import { Construct } from "constructs";

export interface GatewayStackProps extends cdk.StackProps {
  erpDataLambdaArn: string;
  auditLambdaArn: string;
}

export class GatewayStack extends cdk.Stack {
  public readonly gatewayUrl: string;
  public readonly tokenEndpointUrl: string;
  public readonly oauthScopes: string[];

  constructor(scope: Construct, id: string, props: GatewayStackProps) {
    super(scope, id, props);

    // Gateway with default Cognito M2M auth (auto-creates User Pool + Client)
    const gateway = new agentcore.Gateway(this, "McpGateway", {
      gatewayName: "disruptionai-mcp-gateway",
      description: "MCP Gateway for DisruptionAI ERP Data and Audit tools",
      exceptionLevel: agentcore.GatewayExceptionLevel.DEBUG,
    });

    // Import Lambda functions from McpLambdaStack (sameEnvironment allows permission grants)
    const erpDataLambda = lambda.Function.fromFunctionAttributes(
      this, "ErpDataLambda", {
        functionArn: props.erpDataLambdaArn,
        sameEnvironment: true,
      },
    );
    const auditLambda = lambda.Function.fromFunctionAttributes(
      this, "AuditLambda", {
        functionArn: props.auditLambdaArn,
        sameEnvironment: true,
      },
    );

    // --- ERP Data MCP Lambda Target ---
    gateway.addLambdaTarget("ErpDataTarget", {
      gatewayTargetName: "erp-data-mcp",
      description: "ERP Data MCP tools — orders, capacity, customers, materials, tracker",
      lambdaFunction: erpDataLambda,
      toolSchema: agentcore.ToolSchema.fromInline([
        {
          name: "get_orders_tool",
          description: "Get manufacturing orders filtered by plant and/or status",
          inputSchema: {
            type: agentcore.SchemaDefinitionType.OBJECT,
            properties: {
              action_name: { type: agentcore.SchemaDefinitionType.STRING, description: "Must be get_orders_tool" },
              plant: { type: agentcore.SchemaDefinitionType.STRING, description: "Plant name (Florida or Ohio)" },
              status: { type: agentcore.SchemaDefinitionType.STRING, description: "Order status filter (Active, Delayed, etc.)" },
            },
            required: ["action_name"],
          },
        },
        {
          name: "get_order_by_id_tool",
          description: "Get a single order by its order_id",
          inputSchema: {
            type: agentcore.SchemaDefinitionType.OBJECT,
            properties: {
              action_name: { type: agentcore.SchemaDefinitionType.STRING, description: "Must be get_order_by_id_tool" },
              order_id: { type: agentcore.SchemaDefinitionType.STRING, description: "The order ID" },
            },
            required: ["action_name", "order_id"],
          },
        },
        {
          name: "update_order_priority_tool",
          description: "Update the priority of an order (P1, P2, P3)",
          inputSchema: {
            type: agentcore.SchemaDefinitionType.OBJECT,
            properties: {
              action_name: { type: agentcore.SchemaDefinitionType.STRING, description: "Must be update_order_priority_tool" },
              order_id: { type: agentcore.SchemaDefinitionType.STRING, description: "The order ID" },
              priority: { type: agentcore.SchemaDefinitionType.STRING, description: "Priority level (P1, P2, P3)" },
              score: { type: agentcore.SchemaDefinitionType.NUMBER, description: "Priority score (0-100)" },
            },
            required: ["action_name", "order_id", "priority", "score"],
          },
        },
        {
          name: "update_order_status_tool",
          description: "Update the status of an order",
          inputSchema: {
            type: agentcore.SchemaDefinitionType.OBJECT,
            properties: {
              action_name: { type: agentcore.SchemaDefinitionType.STRING, description: "Must be update_order_status_tool" },
              order_id: { type: agentcore.SchemaDefinitionType.STRING, description: "The order ID" },
              status: { type: agentcore.SchemaDefinitionType.STRING, description: "New status" },
            },
            required: ["action_name", "order_id", "status"],
          },
        },
        {
          name: "get_machine_capacity_tool",
          description: "Get machine capacity data for a plant",
          inputSchema: {
            type: agentcore.SchemaDefinitionType.OBJECT,
            properties: {
              action_name: { type: agentcore.SchemaDefinitionType.STRING, description: "Must be get_machine_capacity_tool" },
              plant: { type: agentcore.SchemaDefinitionType.STRING, description: "Plant name" },
            },
            required: ["action_name"],
          },
        },
        {
          name: "get_workforce_tool",
          description: "Get workforce availability data for all plants",
          inputSchema: {
            type: agentcore.SchemaDefinitionType.OBJECT,
            properties: {
              action_name: { type: agentcore.SchemaDefinitionType.STRING, description: "Must be get_workforce_tool" },
            },
            required: ["action_name"],
          },
        },
        {
          name: "get_materials_tool",
          description: "Get raw materials inventory data",
          inputSchema: {
            type: agentcore.SchemaDefinitionType.OBJECT,
            properties: {
              action_name: { type: agentcore.SchemaDefinitionType.STRING, description: "Must be get_materials_tool" },
              plant: { type: agentcore.SchemaDefinitionType.STRING, description: "Plant name filter" },
            },
            required: ["action_name"],
          },
        },
        {
          name: "get_customers_tool",
          description: "Get customer data including tier and SLA information",
          inputSchema: {
            type: agentcore.SchemaDefinitionType.OBJECT,
            properties: {
              action_name: { type: agentcore.SchemaDefinitionType.STRING, description: "Must be get_customers_tool" },
              customer_id: { type: agentcore.SchemaDefinitionType.STRING, description: "Optional customer ID filter" },
            },
            required: ["action_name"],
          },
        },
        {
          name: "get_running_tracker_tool",
          description: "Get the running capacity tracker for a session",
          inputSchema: {
            type: agentcore.SchemaDefinitionType.OBJECT,
            properties: {
              action_name: { type: agentcore.SchemaDefinitionType.STRING, description: "Must be get_running_tracker_tool" },
              session_id: { type: agentcore.SchemaDefinitionType.STRING, description: "Session ID" },
            },
            required: ["action_name", "session_id"],
          },
        },
        {
          name: "update_running_tracker_tool",
          description: "Update the running capacity tracker after an order decision",
          inputSchema: {
            type: agentcore.SchemaDefinitionType.OBJECT,
            properties: {
              action_name: { type: agentcore.SchemaDefinitionType.STRING, description: "Must be update_running_tracker_tool" },
              session_id: { type: agentcore.SchemaDefinitionType.STRING, description: "Session ID" },
              order_id: { type: agentcore.SchemaDefinitionType.STRING, description: "Order ID being decided" },
              decision: { type: agentcore.SchemaDefinitionType.STRING, description: "Decision (approve/reject)" },
              rolling_mill_hours: { type: agentcore.SchemaDefinitionType.NUMBER, description: "Hours consumed" },
              finishing_line_hours: { type: agentcore.SchemaDefinitionType.NUMBER, description: "Hours consumed" },
            },
            required: ["action_name", "session_id"],
          },
        },
        {
          name: "reset_seed_data_tool",
          description: "Reset DynamoDB tables to seed data state",
          inputSchema: {
            type: agentcore.SchemaDefinitionType.OBJECT,
            properties: {
              action_name: { type: agentcore.SchemaDefinitionType.STRING, description: "Must be reset_seed_data_tool" },
              mode: { type: agentcore.SchemaDefinitionType.STRING, description: "Reset mode (full or orders_only)" },
            },
            required: ["action_name"],
          },
        },
      ]),
    });

    // --- Audit MCP Lambda Target ---
    gateway.addLambdaTarget("AuditTarget", {
      gatewayTargetName: "audit-mcp",
      description: "Audit MCP tools — decision logging and compliance trail",
      lambdaFunction: auditLambda,
      toolSchema: agentcore.ToolSchema.fromInline([
        {
          name: "write_audit_entry_tool",
          description: "Write an audit trail entry for a decision or action",
          inputSchema: {
            type: agentcore.SchemaDefinitionType.OBJECT,
            properties: {
              action_name: { type: agentcore.SchemaDefinitionType.STRING, description: "Must be write_audit_entry_tool" },
              session_id: { type: agentcore.SchemaDefinitionType.STRING, description: "Session ID" },
              action: { type: agentcore.SchemaDefinitionType.STRING, description: "Action type" },
              agent: { type: agentcore.SchemaDefinitionType.STRING, description: "Agent name" },
              details: { type: agentcore.SchemaDefinitionType.STRING, description: "Action details" },
              order_id: { type: agentcore.SchemaDefinitionType.STRING, description: "Related order ID" },
            },
            required: ["action_name", "session_id", "action", "agent"],
          },
        },
        {
          name: "get_audit_trail_tool",
          description: "Retrieve audit trail entries for a session",
          inputSchema: {
            type: agentcore.SchemaDefinitionType.OBJECT,
            properties: {
              action_name: { type: agentcore.SchemaDefinitionType.STRING, description: "Must be get_audit_trail_tool" },
              session_id: { type: agentcore.SchemaDefinitionType.STRING, description: "Session ID" },
            },
            required: ["action_name", "session_id"],
          },
        },
      ]),
    });

    // Export gateway URL and Cognito credentials
    this.gatewayUrl = gateway.gatewayUrl ?? "";
    this.tokenEndpointUrl = gateway.tokenEndpointUrl ?? "";
    this.oauthScopes = gateway.oauthScopes ?? [];

    new cdk.CfnOutput(this, "GatewayUrl", {
      value: gateway.gatewayUrl ?? "PENDING",
      exportName: "disruptionai-gateway-url",
    });

    new cdk.CfnOutput(this, "GatewayId", {
      value: gateway.gatewayId,
      exportName: "disruptionai-gateway-id",
    });

    new cdk.CfnOutput(this, "TokenEndpointUrl", {
      value: gateway.tokenEndpointUrl ?? "PENDING",
      exportName: "disruptionai-gateway-token-endpoint",
    });
  }
}
