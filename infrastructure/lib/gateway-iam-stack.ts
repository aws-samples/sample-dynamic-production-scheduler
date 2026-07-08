import * as cdk from "aws-cdk-lib";
import * as iam from "aws-cdk-lib/aws-iam";
import { Construct } from "constructs";

export interface GatewayIamStackProps extends cdk.StackProps {
  erpDataLambdaArn: string;
  auditLambdaArn: string;
  cognitoUserPoolArn: string;
}

export class GatewayIamStack extends cdk.Stack {
  public readonly gatewayManagementRoleArn: string;

  constructor(scope: Construct, id: string, props: GatewayIamStackProps) {
    super(scope, id, props);

    // Gateway management role for setup scripts and gateway service (SECURITY-06)
    const gatewayRole = new iam.Role(this, "GatewayManagementRole", {
      roleName: "disruptionai-gateway-management-role",
      assumedBy: new iam.CompositePrincipal(
        new iam.AccountPrincipal(cdk.Aws.ACCOUNT_ID),
        new iam.ServicePrincipal("bedrock-agentcore.amazonaws.com"),
      ),
    });

    // AgentCore Gateway CRUD operations
    gatewayRole.addToPolicy(
      new iam.PolicyStatement({
        sid: "AgentCoreGatewayManagement",
        actions: [
          "bedrock-agentcore:CreateGateway",
          "bedrock-agentcore:GetGateway",
          "bedrock-agentcore:DeleteGateway",
          "bedrock-agentcore:UpdateGateway",
        ],
        resources: [
          `arn:aws:bedrock-agentcore:${cdk.Aws.REGION}:${cdk.Aws.ACCOUNT_ID}:gateway/*`,
        ],
      })
    );

    // AgentCore Gateway Target CRUD operations
    gatewayRole.addToPolicy(
      new iam.PolicyStatement({
        sid: "AgentCoreGatewayTargetManagement",
        actions: [
          "bedrock-agentcore:CreateGatewayTarget",
          "bedrock-agentcore:GetGatewayTarget",
          "bedrock-agentcore:DeleteGatewayTarget",
          "bedrock-agentcore:UpdateGatewayTarget",
        ],
        resources: [
          `arn:aws:bedrock-agentcore:${cdk.Aws.REGION}:${cdk.Aws.ACCOUNT_ID}:gateway/*`,
        ],
      })
    );

    // Lambda invocation for both MCP functions
    gatewayRole.addToPolicy(
      new iam.PolicyStatement({
        sid: "LambdaInvokeMcpFunctions",
        actions: ["lambda:InvokeFunction"],
        resources: [props.erpDataLambdaArn, props.auditLambdaArn],
      })
    );

    // Cognito User Pool describe for gateway auth configuration
    gatewayRole.addToPolicy(
      new iam.PolicyStatement({
        sid: "CognitoDescribeUserPool",
        actions: ["cognito-idp:DescribeUserPool"],
        resources: [props.cognitoUserPoolArn],
      })
    );

    this.gatewayManagementRoleArn = gatewayRole.roleArn;

    // Outputs
    new cdk.CfnOutput(this, "GatewayManagementRoleArn", {
      value: gatewayRole.roleArn,
      exportName: "disruptionai-gateway-management-role-arn",
    });
  }
}
