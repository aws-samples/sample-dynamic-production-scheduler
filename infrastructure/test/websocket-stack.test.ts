import * as cdk from "aws-cdk-lib";
import { Template } from "aws-cdk-lib/assertions";
import * as logs from "aws-cdk-lib/aws-logs";
import { WebSocketStack } from "../lib/websocket-stack";

describe("WebSocketStack", () => {
  let template: Template;

  beforeAll(() => {
    const app = new cdk.App();
    const logStack = new cdk.Stack(app, "LogStack");
    const logGroup = new logs.LogGroup(logStack, "TestLog", {
      logGroupName: "/disruptionai/websocket-api",
    });
    const stack = new WebSocketStack(app, "TestWebSocket", {
      logGroup,
    });
    template = Template.fromStack(stack);
  });

  test("creates WebSocket API", () => {
    template.hasResourceProperties("AWS::ApiGatewayV2::Api", {
      Name: "disruptionai-websocket",
      ProtocolType: "WEBSOCKET",
    });
  });

  test("creates 3 routes", () => {
    template.resourceCountIs("AWS::ApiGatewayV2::Route", 3);
  });

  test("creates Lambda handler", () => {
    template.hasResourceProperties("AWS::Lambda::Function", {
      FunctionName: "disruptionai-ws-handler",
      Runtime: "python3.11",
      Timeout: 30,
      MemorySize: 256,
    });
  });

  test("creates prod stage", () => {
    template.hasResourceProperties("AWS::ApiGatewayV2::Stage", {
      StageName: "prod",
    });
  });

  test("exports WebSocket URL and API ID", () => {
    template.hasOutput("WebSocketUrl", {});
    template.hasOutput("WebSocketApiId", {});
  });
});
