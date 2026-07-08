import * as cdk from "aws-cdk-lib";
import { Template } from "aws-cdk-lib/assertions";
import { MonitoringStack } from "../lib/monitoring-stack";

describe("MonitoringStack", () => {
  let template: Template;

  beforeAll(() => {
    const app = new cdk.App();
    const stack = new MonitoringStack(app, "TestMonitoring");
    template = Template.fromStack(stack);
  });

  test("creates 7 CloudWatch log groups", () => {
    template.resourceCountIs("AWS::Logs::LogGroup", 7);
  });

  test("log groups have 90-day retention", () => {
    const logGroups = template.findResources("AWS::Logs::LogGroup");
    for (const [, resource] of Object.entries(logGroups)) {
      expect((resource as any).Properties.RetentionInDays).toBe(90);
    }
  });

  test("creates CloudWatch dashboard", () => {
    template.resourceCountIs("AWS::CloudWatch::Dashboard", 1);
  });

  test("creates DynamoDB throttle alarm", () => {
    template.hasResourceProperties("AWS::CloudWatch::Alarm", {
      AlarmName: "disruptionai-dynamodb-throttle",
      Threshold: 10,
      EvaluationPeriods: 2,
    });
  });

  test("creates error metric filters for log groups", () => {
    template.resourceCountIs("AWS::Logs::MetricFilter", 7);
  });
});
