import * as cdk from "aws-cdk-lib";
import { Template, Match } from "aws-cdk-lib/assertions";
import { IamStack } from "../lib/iam-stack";
import { TableArns } from "../lib/database-stack";

describe("IamStack", () => {
  let template: Template;

  const mockTableArns: TableArns = {
    orders: "arn:aws:dynamodb:us-east-1:123456789012:table/disruptionai-orders",
    ordersIndex:
      "arn:aws:dynamodb:us-east-1:123456789012:table/disruptionai-orders/index/*",
    capacity:
      "arn:aws:dynamodb:us-east-1:123456789012:table/disruptionai-capacity",
    workforce:
      "arn:aws:dynamodb:us-east-1:123456789012:table/disruptionai-manpower",
    materials:
      "arn:aws:dynamodb:us-east-1:123456789012:table/disruptionai-materials",
    customers:
      "arn:aws:dynamodb:us-east-1:123456789012:table/disruptionai-customers",
    tracker:
      "arn:aws:dynamodb:us-east-1:123456789012:table/disruptionai-tracker",
    audit: "arn:aws:dynamodb:us-east-1:123456789012:table/disruptionai-audit",
    auditIndex:
      "arn:aws:dynamodb:us-east-1:123456789012:table/disruptionai-audit/index/*",
  };

  beforeAll(() => {
    const app = new cdk.App();
    const stack = new IamStack(app, "TestIAM", {
      tableArns: mockTableArns,
      logGroupArns: [
        "arn:aws:logs:us-east-1:123456789012:log-group:/disruptionai/test",
      ],
    });
    template = Template.fromStack(stack);
  });

  test("creates ECS task role", () => {
    template.hasResourceProperties("AWS::IAM::Role", {
      RoleName: "disruptionai-ecs-task-role",
      AssumeRolePolicyDocument: {
        Statement: Match.arrayWith([
          Match.objectLike({
            Effect: "Allow",
            Principal: { Service: "ecs-tasks.amazonaws.com" },
          }),
        ]),
      },
    });
  });

  test("creates ECS execution role", () => {
    template.hasResourceProperties("AWS::IAM::Role", {
      RoleName: "disruptionai-ecs-execution-role",
    });
  });

  test("task role has DynamoDB read-only policy", () => {
    template.hasResourceProperties("AWS::IAM::Policy", {
      PolicyDocument: {
        Statement: Match.arrayWith([
          Match.objectLike({
            Sid: "DynamoDBReadOnly",
            Effect: "Allow",
            Action: [
              "dynamodb:GetItem",
              "dynamodb:Query",
              "dynamodb:Scan",
            ],
          }),
        ]),
      },
    });
  });

  test("task role has DynamoDB read-write policy", () => {
    template.hasResourceProperties("AWS::IAM::Policy", {
      PolicyDocument: {
        Statement: Match.arrayWith([
          Match.objectLike({
            Sid: "DynamoDBReadWrite",
            Effect: "Allow",
            Action: Match.arrayWith([
              "dynamodb:PutItem",
              "dynamodb:UpdateItem",
            ]),
          }),
        ]),
      },
    });
  });

  test("task role has Bedrock invoke policy", () => {
    template.hasResourceProperties("AWS::IAM::Policy", {
      PolicyDocument: {
        Statement: Match.arrayWith([
          Match.objectLike({
            Sid: "BedrockInvoke",
            Effect: "Allow",
            Action: [
              "bedrock:InvokeModel",
              "bedrock:InvokeModelWithResponseStream",
            ],
          }),
        ]),
      },
    });
  });

  test("task role cannot delete CloudWatch logs (SECURITY-14)", () => {
    template.hasResourceProperties("AWS::IAM::Policy", {
      PolicyDocument: {
        Statement: Match.arrayWith([
          Match.objectLike({
            Sid: "CloudWatchLogs",
            Action: [
              "logs:CreateLogStream",
              "logs:PutLogEvents",
            ],
          }),
        ]),
      },
    });
  });

  test("no wildcard actions in any policy (SECURITY-06)", () => {
    const policies = template.findResources("AWS::IAM::Policy");
    for (const [, resource] of Object.entries(policies)) {
      const statements = (resource as any).Properties.PolicyDocument.Statement;
      for (const stmt of statements) {
        const actions = Array.isArray(stmt.Action)
          ? stmt.Action
          : [stmt.Action];
        for (const action of actions) {
          expect(action).not.toBe("*");
          expect(action).not.toContain(":*");
        }
      }
    }
  });

  test("exports role ARNs", () => {
    template.hasOutput("EcsTaskRoleArn", {});
    template.hasOutput("EcsExecutionRoleArn", {});
  });
});
