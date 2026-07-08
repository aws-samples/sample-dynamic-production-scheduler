import * as cdk from "aws-cdk-lib";
import * as lambda from "aws-cdk-lib/aws-lambda";
import * as iam from "aws-cdk-lib/aws-iam";
import * as logs from "aws-cdk-lib/aws-logs";
import { Construct } from "constructs";
import { TableArns } from "./database-stack";

export interface McpLambdaStackProps extends cdk.StackProps {
  tableArns: TableArns;
}

export class McpLambdaStack extends cdk.Stack {
  public readonly erpDataLambdaArn: string;
  public readonly auditLambdaArn: string;

  constructor(scope: Construct, id: string, props: McpLambdaStackProps) {
    super(scope, id, props);

    // ---------------------------------------------------------------
    // ERP Data MCP Lambda
    // ---------------------------------------------------------------

    // CloudWatch log group with 90-day retention (SECURITY-14)
    const erpDataLogGroup = new logs.LogGroup(this, "ErpDataLogGroup", {
      logGroupName: "/aws/lambda/disruptionai-erp-data-mcp",
      retention: logs.RetentionDays.THREE_MONTHS,
      removalPolicy: cdk.RemovalPolicy.DESTROY,
    });

    // Execution role — least-privilege DynamoDB access (SECURITY-06)
    const erpDataRole = new iam.Role(this, "ErpDataRole", {
      roleName: "disruptionai-erp-data-mcp-role",
      assumedBy: new iam.ServicePrincipal("lambda.amazonaws.com"),
    });

    // CloudWatch Logs write
    erpDataRole.addToPolicy(
      new iam.PolicyStatement({
        sid: "CloudWatchLogs",
        actions: ["logs:CreateLogStream", "logs:PutLogEvents"],
        resources: [erpDataLogGroup.logGroupArn + ":*"],
      })
    );

    // DynamoDB read-only: capacity, workforce, materials, customers
    erpDataRole.addToPolicy(
      new iam.PolicyStatement({
        sid: "DynamoDBReadOnly",
        actions: ["dynamodb:GetItem", "dynamodb:Query", "dynamodb:Scan"],
        resources: [
          props.tableArns.capacity,
          props.tableArns.workforce,
          props.tableArns.materials,
          props.tableArns.customers,
        ],
      })
    );

    // DynamoDB read-write: orders (+ index), tracker
    erpDataRole.addToPolicy(
      new iam.PolicyStatement({
        sid: "DynamoDBReadWrite",
        actions: [
          "dynamodb:GetItem",
          "dynamodb:Query",
          "dynamodb:Scan",
          "dynamodb:PutItem",
          "dynamodb:UpdateItem",
        ],
        resources: [
          props.tableArns.orders,
          props.tableArns.ordersIndex,
          props.tableArns.tracker,
          props.tableArns.workflowState,
        ],
      })
    );

    const erpDataLambda = new lambda.Function(this, "ErpDataMcpFunction", {
      functionName: "disruptionai-erp-data-mcp",
      runtime: lambda.Runtime.PYTHON_3_13,
      handler: "erp_data_mcp.lambda_handler.handler",
      code: lambda.Code.fromAsset("../erp-data-mcp/.lambda-bundle"),
      role: erpDataRole,
      memorySize: 512,
      timeout: cdk.Duration.seconds(30),
      logGroup: erpDataLogGroup,
      environment: {
        AWS_REGION_NAME: "us-east-1",
      },
    });

    this.erpDataLambdaArn = erpDataLambda.functionArn;

    // ---------------------------------------------------------------
    // Audit MCP Lambda
    // ---------------------------------------------------------------

    // CloudWatch log group with 90-day retention (SECURITY-14)
    const auditLogGroup = new logs.LogGroup(this, "AuditLogGroup", {
      logGroupName: "/aws/lambda/disruptionai-audit-mcp",
      retention: logs.RetentionDays.THREE_MONTHS,
      removalPolicy: cdk.RemovalPolicy.DESTROY,
    });

    // Execution role — least-privilege DynamoDB access (SECURITY-06)
    const auditRole = new iam.Role(this, "AuditRole", {
      roleName: "disruptionai-audit-mcp-role",
      assumedBy: new iam.ServicePrincipal("lambda.amazonaws.com"),
    });

    // CloudWatch Logs write
    auditRole.addToPolicy(
      new iam.PolicyStatement({
        sid: "CloudWatchLogs",
        actions: ["logs:CreateLogStream", "logs:PutLogEvents"],
        resources: [auditLogGroup.logGroupArn + ":*"],
      })
    );

    // DynamoDB read-write: audit table + index
    auditRole.addToPolicy(
      new iam.PolicyStatement({
        sid: "DynamoDBAuditReadWrite",
        actions: [
          "dynamodb:GetItem",
          "dynamodb:Query",
          "dynamodb:PutItem",
        ],
        resources: [
          props.tableArns.audit,
          props.tableArns.auditIndex,
        ],
      })
    );

    const auditLambda = new lambda.Function(this, "AuditMcpFunction", {
      functionName: "disruptionai-audit-mcp",
      runtime: lambda.Runtime.PYTHON_3_13,
      handler: "audit_mcp.lambda_handler.handler",
      code: lambda.Code.fromAsset("../audit-mcp/.lambda-bundle"),
      role: auditRole,
      memorySize: 256,
      timeout: cdk.Duration.seconds(15),
      logGroup: auditLogGroup,
      environment: {
        AWS_REGION_NAME: "us-east-1",
      },
    });

    this.auditLambdaArn = auditLambda.functionArn;

    // Outputs
    new cdk.CfnOutput(this, "ErpDataLambdaArn", {
      value: erpDataLambda.functionArn,
      exportName: "disruptionai-erp-data-mcp-lambda-arn",
    });

    new cdk.CfnOutput(this, "AuditLambdaArn", {
      value: auditLambda.functionArn,
      exportName: "disruptionai-audit-mcp-lambda-arn",
    });
  }
}
