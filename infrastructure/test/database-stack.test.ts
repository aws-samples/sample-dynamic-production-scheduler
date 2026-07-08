import * as cdk from "aws-cdk-lib";
import { Template } from "aws-cdk-lib/assertions";
import { DatabaseStack } from "../lib/database-stack";

describe("DatabaseStack", () => {
  let template: Template;

  beforeAll(() => {
    const app = new cdk.App();
    const stack = new DatabaseStack(app, "TestDatabase");
    template = Template.fromStack(stack);
  });

  test("creates 7 DynamoDB tables", () => {
    template.resourceCountIs("AWS::DynamoDB::Table", 7);
  });

  test("orders table has correct key schema", () => {
    template.hasResourceProperties("AWS::DynamoDB::Table", {
      TableName: "disruptionai-orders",
      KeySchema: [
        { AttributeName: "order_id", KeyType: "HASH" },
      ],
      BillingMode: "PAY_PER_REQUEST",
    });
  });

  test("orders table has plant-status GSI", () => {
    template.hasResourceProperties("AWS::DynamoDB::Table", {
      TableName: "disruptionai-orders",
      GlobalSecondaryIndexes: [
        {
          IndexName: "plant-status-index",
          KeySchema: [
            { AttributeName: "plant", KeyType: "HASH" },
            { AttributeName: "status", KeyType: "RANGE" },
          ],
          Projection: { ProjectionType: "ALL" },
        },
      ],
    });
  });

  test("audit table has PITR enabled", () => {
    template.hasResourceProperties("AWS::DynamoDB::Table", {
      TableName: "disruptionai-audit",
      PointInTimeRecoverySpecification: {
        PointInTimeRecoveryEnabled: true,
      },
    });
  });

  test("audit table has session-agent GSI", () => {
    template.hasResourceProperties("AWS::DynamoDB::Table", {
      TableName: "disruptionai-audit",
      GlobalSecondaryIndexes: [
        {
          IndexName: "session-agent-index",
          KeySchema: [
            { AttributeName: "session_id", KeyType: "HASH" },
            { AttributeName: "agent", KeyType: "RANGE" },
          ],
          Projection: { ProjectionType: "ALL" },
        },
      ],
    });
  });

  test("capacity table has composite key", () => {
    template.hasResourceProperties("AWS::DynamoDB::Table", {
      TableName: "disruptionai-capacity",
      KeySchema: [
        { AttributeName: "machine_type", KeyType: "HASH" },
        { AttributeName: "plant", KeyType: "RANGE" },
      ],
    });
  });

  test("all tables use PAY_PER_REQUEST billing", () => {
    const tables = template.findResources("AWS::DynamoDB::Table");
    for (const [, resource] of Object.entries(tables)) {
      expect((resource as any).Properties.BillingMode).toBe("PAY_PER_REQUEST");
    }
  });

  test("exports table name outputs", () => {
    template.hasOutput("TableNameorders", {});
    template.hasOutput("TableNameaudit", {});
  });
});
