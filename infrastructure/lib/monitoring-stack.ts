import * as cdk from "aws-cdk-lib";
import * as logs from "aws-cdk-lib/aws-logs";
import * as kms from "aws-cdk-lib/aws-kms";
import * as cloudwatch from "aws-cdk-lib/aws-cloudwatch";
import { Construct } from "constructs";

const LOG_GROUPS = [
  "/disruptionai/erp-data-mcp",
  "/disruptionai/audit-mcp",
  "/disruptionai/impact-assessment-agent",
  "/disruptionai/capacity-optimization-agent",
  "/disruptionai/constraint-matching-agent",
  "/disruptionai/orchestrator-agent",
  "/disruptionai/websocket-api",
] as const;

export class MonitoringStack extends cdk.Stack {
  public readonly logGroupArns: string[];
  public readonly websocketLogGroup: logs.ILogGroup;

  constructor(scope: Construct, id: string, props?: cdk.StackProps) {
    super(scope, id, props);

    const logGroups: logs.LogGroup[] = [];

    // KMS key for CloudWatch Logs encryption
    const logEncryptionKey = new kms.Key(this, "LogEncryptionKey", {
      alias: "disruptionai-logs",
      description: "KMS key for DisruptionAI CloudWatch Logs encryption",
      enableKeyRotation: true,
      removalPolicy: cdk.RemovalPolicy.DESTROY,
    });
    // Grant CloudWatch Logs service permission to use the key
    logEncryptionKey.addToResourcePolicy(
      new cdk.aws_iam.PolicyStatement({
        actions: ["kms:Encrypt*", "kms:Decrypt*", "kms:ReEncrypt*", "kms:GenerateDataKey*", "kms:Describe*"],
        principals: [new cdk.aws_iam.ServicePrincipal(`logs.${cdk.Stack.of(this).region}.amazonaws.com`)],
        resources: ["*"],
      })
    );

    for (const name of LOG_GROUPS) {
      const lg = new logs.LogGroup(this, logGroupId(name), {
        logGroupName: name,
        retention: logs.RetentionDays.THREE_MONTHS,
        removalPolicy: cdk.RemovalPolicy.DESTROY,
        encryptionKey: logEncryptionKey,
      });
      logGroups.push(lg);
    }

    this.logGroupArns = logGroups.map((lg) => lg.logGroupArn);
    this.websocketLogGroup = logGroups[logGroups.length - 1];

    // CloudWatch Dashboard
    const dashboard = new cloudwatch.Dashboard(this, "Dashboard", {
      dashboardName: "DisruptionAI-Overview",
    });

    dashboard.addWidgets(
      new cloudwatch.TextWidget({
        markdown: "# DisruptionAI Monitoring Dashboard",
        width: 24,
        height: 1,
      })
    );

    // DynamoDB throttle alarm
    const throttleMetric = new cloudwatch.Metric({
      namespace: "AWS/DynamoDB",
      metricName: "ThrottledRequests",
      dimensionsMap: { TableName: "disruptionai-orders" },
      statistic: "Sum",
      period: cdk.Duration.minutes(5),
    });

    new cloudwatch.Alarm(this, "DynamoDBThrottleAlarm", {
      alarmName: "disruptionai-dynamodb-throttle",
      metric: throttleMetric,
      threshold: 10,
      evaluationPeriods: 2,
      comparisonOperator:
        cloudwatch.ComparisonOperator.GREATER_THAN_THRESHOLD,
      treatMissingData: cloudwatch.TreatMissingData.NOT_BREACHING,
    });

    // Error metric filter for each log group
    for (const lg of logGroups) {
      const filter = lg.addMetricFilter(`${lg.node.id}-ErrorFilter`, {
        filterPattern: logs.FilterPattern.literal("ERROR"),
        metricNamespace: "DisruptionAI",
        metricName: `${lg.node.id}-Errors`,
        metricValue: "1",
      });
    }
  }
}

function logGroupId(name: string): string {
  return name
    .replace(/^\/disruptionai\//, "")
    .replace(/-/g, "")
    .replace(/\b\w/g, (c) => c.toUpperCase())
    + "LogGroup";
}
