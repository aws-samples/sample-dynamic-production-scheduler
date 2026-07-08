#!/usr/bin/env node
import "source-map-support/register";
import * as cdk from "aws-cdk-lib";
import { DatabaseStack } from "../lib/database-stack";
import { MonitoringStack } from "../lib/monitoring-stack";
import { IamStack } from "../lib/iam-stack";
import { FrontendStack } from "../lib/frontend-stack";
import { WebSocketStack } from "../lib/websocket-stack";
import { CognitoStack } from "../lib/cognito-stack";
import { McpLambdaStack } from "../lib/mcp-lambda-stack";
import { GatewayIamStack } from "../lib/gateway-iam-stack";
import { RestProxyStack } from "../lib/rest-proxy-stack";
import { AgentCoreStack } from "../lib/agentcore-stack";
import { GatewayStack } from "../lib/gateway-stack";

const app = new cdk.App();

const env: cdk.Environment = {
  account: process.env.CDK_DEFAULT_ACCOUNT,
  region: process.env.CDK_DEFAULT_REGION ?? "us-east-1",
};

const database = new DatabaseStack(app, "DisruptionAI-Database", { env });

const monitoring = new MonitoringStack(app, "DisruptionAI-Monitoring", { env });

const iam = new IamStack(app, "DisruptionAI-IAM", {
  env,
  tableArns: database.tableArns,
  logGroupArns: monitoring.logGroupArns,
});

const websocket = new WebSocketStack(app, "DisruptionAI-WebSocket", {
  env,
  logGroup: monitoring.websocketLogGroup,
});

// Cognito for frontend user auth
const cognitoStack = new CognitoStack(app, "DisruptionAI-Cognito", { env });

// MCP Lambda functions (ERP Data + Audit)
const mcpLambda = new McpLambdaStack(app, "DisruptionAI-McpLambda", {
  env,
  tableArns: database.tableArns,
});

// Legacy Gateway IAM (kept for backward compatibility)
new GatewayIamStack(app, "DisruptionAI-GatewayIam", {
  env,
  erpDataLambdaArn: mcpLambda.erpDataLambdaArn,
  auditLambdaArn: mcpLambda.auditLambdaArn,
  cognitoUserPoolArn: cognitoStack.userPoolArn,
});

// AgentCore Gateway (CDK-managed, auto-creates Cognito M2M auth)
const gatewayStack = new GatewayStack(app, "DisruptionAI-Gateway", {
  env,
  erpDataLambdaArn: mcpLambda.erpDataLambdaArn,
  auditLambdaArn: mcpLambda.auditLambdaArn,
});

// AgentCore Runtimes + Memory (deployed via CDK, no CLI needed)
const agentCoreStack = new AgentCoreStack(app, "DisruptionAI-AgentCore", {
  env,
  gatewayUrl: gatewayStack.gatewayUrl,
  cognitoTokenEndpoint: gatewayStack.tokenEndpointUrl,
});

const restProxy = new RestProxyStack(app, "DisruptionAI-RestProxy", {
  env,
  logGroup: monitoring.websocketLogGroup,
  authenticatedRoleArn: cognitoStack.authenticatedRoleArn,
});

new FrontendStack(app, "DisruptionAI-Frontend", {
  env,
  websocketApiUrl: websocket.websocketUrl,
  restProxyUrl: restProxy.functionUrl,
});

app.synth();
