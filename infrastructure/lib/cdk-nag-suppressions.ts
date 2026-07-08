import { NagSuppressions } from "cdk-nag";
import * as cdk from "aws-cdk-lib";

export function applyCdkNagSuppressions(app: cdk.App): void {
  const suppressions = [
    { id: "AwsSolutions-IAM5", reason: "Wildcards required: log-group ARNs need :* per CloudWatch API, DynamoDB index ARNs use /index/*, Bedrock AgentCore runtime IDs are generated at deploy time" },
    { id: "AwsSolutions-IAM4", reason: "AWS managed policy AmazonECSTaskExecutionRolePolicy is the AWS-recommended pattern for ECS task execution" },
    { id: "AwsSolutions-L1", reason: "Lambda functions use Python 3.13 which is the latest available runtime; cdk-nag version check may not recognize it" },
    { id: "AwsSolutions-COG1", reason: "Demo application — password policy changes would lock out existing demo users" },
    { id: "AwsSolutions-COG2", reason: "Demo application — MFA not required for internal demo usage" },
    { id: "AwsSolutions-COG8", reason: "Cognito Plus tier not required for demo application (cost consideration)" },
    { id: "AwsSolutions-APIG4", reason: "WebSocket API: authorization is enforced on $connect route; disconnect and sendMessage routes inherit the authenticated connection (API Gateway WebSocket limitation)" },
    { id: "AwsSolutions-APIG1", reason: "WebSocket API access logging configured at stage level via defaultRouteSettings" },
    { id: "AwsSolutions-CFR1", reason: "Demo application — geo restriction not required" },
    { id: "AwsSolutions-CFR2", reason: "Demo application — WAF not required (adds cost)" },
    { id: "AwsSolutions-CFR4", reason: "Demo application — using default CloudFront certificate; custom domain/cert not configured" },
    { id: "AwsSolutions-CFR7", reason: "Demo application — WAF not required (adds cost)" },
  ];

  // IAM5: Wildcard permissions required by CloudWatch Logs API (log-group ARNs need :* suffix)
  // and DynamoDB GSI access (table/*/index/*), and Bedrock AgentCore (generated runtime IDs)
  const stacks = app.node.findAll().filter((c): c is cdk.Stack => c instanceof cdk.Stack);
  for (const stack of stacks) {
    NagSuppressions.addStackSuppressions(stack, suppressions, true);
  }
}
