import * as cdk from "aws-cdk-lib";
import * as iam from "aws-cdk-lib/aws-iam";
import { Construct } from "constructs";
import { TableArns } from "./database-stack";

export interface IamStackProps extends cdk.StackProps {
  tableArns: TableArns;
  logGroupArns: string[];
}

export class IamStack extends cdk.Stack {
  public readonly ecsTaskRole: iam.Role;
  public readonly ecsExecutionRole: iam.Role;

  constructor(scope: Construct, id: string, props: IamStackProps) {
    super(scope, id, props);

    // ECS Task Execution Role (pulls images, writes logs)
    this.ecsExecutionRole = new iam.Role(this, "EcsExecutionRole", {
      roleName: "disruptionai-ecs-execution-role",
      assumedBy: new iam.ServicePrincipal("ecs-tasks.amazonaws.com"),
      managedPolicies: [
        iam.ManagedPolicy.fromAwsManagedPolicyName(
          "service-role/AmazonECSTaskExecutionRolePolicy"
        ),
      ],
    });

    // ECS Task Role (application permissions)
    this.ecsTaskRole = new iam.Role(this, "EcsTaskRole", {
      roleName: "disruptionai-ecs-task-role",
      assumedBy: new iam.ServicePrincipal("ecs-tasks.amazonaws.com"),
    });

    // DynamoDB read-only tables (SECURITY-06: specific actions + ARNs)
    this.ecsTaskRole.addToPolicy(
      new iam.PolicyStatement({
        sid: "DynamoDBReadOnly",
        actions: [
          "dynamodb:GetItem",
          "dynamodb:Query",
          "dynamodb:Scan",
        ],
        resources: [
          props.tableArns.capacity,
          props.tableArns.workforce,
          props.tableArns.materials,
          props.tableArns.customers,
        ],
      })
    );

    // DynamoDB read-write tables (orders + tracker)
    this.ecsTaskRole.addToPolicy(
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
        ],
      })
    );

    // DynamoDB audit table (read + write)
    this.ecsTaskRole.addToPolicy(
      new iam.PolicyStatement({
        sid: "DynamoDBAudit",
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

    // DynamoDB seed data (BatchWriteItem for initial load)
    this.ecsTaskRole.addToPolicy(
      new iam.PolicyStatement({
        sid: "DynamoDBSeed",
        actions: ["dynamodb:BatchWriteItem"],
        resources: [
          props.tableArns.orders,
          props.tableArns.capacity,
          props.tableArns.workforce,
          props.tableArns.materials,
          props.tableArns.customers,
        ],
      })
    );

    // CloudWatch Logs (SECURITY-14: write only, cannot delete)
    this.ecsTaskRole.addToPolicy(
      new iam.PolicyStatement({
        sid: "CloudWatchLogs",
        actions: [
          "logs:CreateLogStream",
          "logs:PutLogEvents",
        ],
        resources: props.logGroupArns.map((arn) => arn + ":*"),
      })
    );

    // Bedrock model invocation (for agents)
    this.ecsTaskRole.addToPolicy(
      new iam.PolicyStatement({
        sid: "BedrockInvoke",
        actions: [
          "bedrock:InvokeModel",
          "bedrock:InvokeModelWithResponseStream",
        ],
        resources: [
          "arn:aws:bedrock:*:*:inference-profile/us.anthropic.claude-4-5-haiku-*",
        ],
      })
    );

    // AgentCore Gateway invocation (for agents connecting via gateway)
    this.ecsTaskRole.addToPolicy(
      new iam.PolicyStatement({
        sid: "AgentCoreGatewayInvoke",
        actions: ["bedrock-agentcore:InvokeGateway"],
        resources: [
          `arn:aws:bedrock-agentcore:${cdk.Aws.REGION}:${cdk.Aws.ACCOUNT_ID}:gateway/*`,
        ],
      })
    );

    // -----------------------------------------------------------------
    // Cross-agent invoke permissions (SECURITY-06)
    //
    // Applied dynamically via:
    //   infrastructure/scripts/apply-cross-agent-permissions.sh
    //
    // AgentCore creates execution roles with unpredictable suffixes.
    // The script discovers all AmazonBedrockAgentCoreSDKRuntime-* roles
    // and attaches the CrossAgentInvoke inline policy to each.
    // Run the script after deploying agents to AgentCore.
    // -----------------------------------------------------------------

    // Outputs
    new cdk.CfnOutput(this, "EcsTaskRoleArn", {
      value: this.ecsTaskRole.roleArn,
      exportName: "disruptionai-ecs-task-role-arn",
    });

    new cdk.CfnOutput(this, "EcsExecutionRoleArn", {
      value: this.ecsExecutionRole.roleArn,
      exportName: "disruptionai-ecs-execution-role-arn",
    });
  }
}
