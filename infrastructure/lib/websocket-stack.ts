import * as cdk from "aws-cdk-lib";
import * as apigatewayv2 from "aws-cdk-lib/aws-apigatewayv2";
import * as lambda from "aws-cdk-lib/aws-lambda";
import * as iam from "aws-cdk-lib/aws-iam";
import * as logs from "aws-cdk-lib/aws-logs";
import { Construct } from "constructs";

export interface WebSocketStackProps extends cdk.StackProps {
  logGroup: logs.ILogGroup;
}

export class WebSocketStack extends cdk.Stack {
  public readonly websocketUrl: string;
  public readonly apiId: string;

  constructor(scope: Construct, id: string, props: WebSocketStackProps) {
    super(scope, id, props);

    // WebSocket handler Lambda
    const handlerRole = new iam.Role(this, "HandlerRole", {
      roleName: "disruptionai-ws-handler-role",
      assumedBy: new iam.ServicePrincipal("lambda.amazonaws.com"),
    });

    handlerRole.addToPolicy(
      new iam.PolicyStatement({
        actions: [
          "logs:CreateLogStream",
          "logs:PutLogEvents",
        ],
        resources: [props.logGroup.logGroupArn + ":*"],
      })
    );

    // Allow Lambda to invoke the Orchestrator Agent on AgentCore Runtime.
    // Scoped to orchestrator_agent runtimes only (least privilege) rather than
    // all runtimes in the account. The runtime name carries a generated suffix,
    // so a prefix wildcard is used.
    handlerRole.addToPolicy(
      new iam.PolicyStatement({
        actions: [
          "bedrock-agentcore:InvokeAgentRuntime",
        ],
        resources: [
          `arn:aws:bedrock-agentcore:${this.region}:${this.account}:runtime/orchestrator_agent-*`,
        ],
      })
    );

    // Note: Using Lambda runtime's built-in boto3
    // If you need a newer boto3 version, create layers/boto3-layer directory
    // and uncomment the layer code below

    const handler = new lambda.Function(this, "WebSocketHandler", {
      functionName: "disruptionai-ws-handler",
      runtime: lambda.Runtime.PYTHON_3_13,
      handler: "index.handler",
      code: lambda.Code.fromInline(`
import json
import logging
import os
import boto3
from botocore.config import Config

logger = logging.getLogger()
logger.setLevel(logging.INFO)

ORCHESTRATOR_AGENT_ARN = os.environ.get("ORCHESTRATOR_AGENT_ARN", "")
REGION = os.environ.get("AWS_REGION", "us-east-1")

agentcore = None
apigw_mgmt_clients = {}

def get_agentcore_client():
    global agentcore
    if agentcore is None:
        cfg = Config(read_timeout=300, connect_timeout=10, retries={"max_attempts": 1})
        agentcore = boto3.client("bedrock-agentcore", region_name=REGION, config=cfg)
    return agentcore

def get_apigw_client(api_url):
    if api_url not in apigw_mgmt_clients:
        apigw_mgmt_clients[api_url] = boto3.client(
            "apigatewaymanagementapi",
            endpoint_url=api_url,
            region_name=REGION,
        )
    return apigw_mgmt_clients[api_url]

def post_to_connection(api_url, connection_id, data):
    """Post a message back to a WebSocket connection via boto3 (SigV4-signed)."""
    try:
        client = get_apigw_client(api_url)
        client.post_to_connection(
            ConnectionId=connection_id,
            Data=json.dumps(data).encode("utf-8"),
        )
    except Exception as e:
        logger.error(f"Failed to post to connection {connection_id}: {e}")

def handler(event, context):
    route = event.get("requestContext", {}).get("routeKey", "")
    connection_id = event.get("requestContext", {}).get("connectionId", "")
    domain = event.get("requestContext", {}).get("domainName", "")
    stage_name = event.get("requestContext", {}).get("stage", "prod")
    api_url = f"https://{domain}/{stage_name}"

    logger.info(json.dumps({
        "route": route,
        "connectionId": connection_id,
    }))

    if route == "$connect":
        return {"statusCode": 200, "body": "Connected"}
    if route == "$disconnect":
        return {"statusCode": 200, "body": "Disconnected"}
    if route == "sendMessage":
        try:
            body = json.loads(event.get("body", "{}"))
            user_message = body.get("data", body.get("message", ""))
            if not user_message:
                return {"statusCode": 400, "body": "No message provided"}

            if not ORCHESTRATOR_AGENT_ARN:
                logger.error("ORCHESTRATOR_AGENT_ARN not set")
                return {"statusCode": 500, "body": "Orchestrator not configured"}

            import hashlib, uuid
            # runtimeSessionId must be >= 33 chars; derive a stable UUID from connection_id
            session_uuid = str(uuid.UUID(hashlib.sha256(connection_id.encode()).hexdigest()[:32]))
            runtime_session_id = f"disruptionai-{session_uuid}"
            message_id = str(uuid.uuid4())

            logger.info(f"Invoking orchestrator: {ORCHESTRATOR_AGENT_ARN}, session: {runtime_session_id}")
            client = get_agentcore_client()
            response = client.invoke_agent_runtime(
                agentRuntimeArn=ORCHESTRATOR_AGENT_ARN,
                runtimeSessionId=runtime_session_id,
                payload=json.dumps({
                    "prompt": user_message,
                    "session_id": connection_id,
                }),
            )

            # Stream response tokens back to the WebSocket connection
            content_type = response.get("contentType", "")
            logger.info(f"Response contentType: {content_type}")

            def send_token(token, done=False):
                post_to_connection(api_url, connection_id, {
                    "type": "stream_token",
                    "payload": {
                        "messageId": message_id,
                        "token": token,
                        "done": done,
                    },
                })

            # Stream signal detection patterns
            import re
            PHASE_KEYWORDS = {
                "impact assessment": "impact_assessment",
                "impact analysis": "impact_assessment",
                "priority classification": "impact_assessment",
                "capacity analysis": "capacity_analysis",
                "capacity optimization": "capacity_analysis",
                "delay optimization": "delay_optimization",
                "delay candidate": "delay_optimization",
                "constraint matching": "constraint_matching",
                "constraint funnel": "constraint_matching",
                "transfer summary": "summary",
                "final summary": "summary",
                "what-if": "what_if",
            }
            AGENT_PATTERNS = {
                "Impact Assessment Agent": "Impact Assessment",
                "Capacity Optimization Agent": "Capacity Optimization",
                "Capacity & Optimization Agent": "Capacity Optimization",
                "Constraint Matching Agent": "Constraint Matching",
            }
            current_phase = None
            token_buffer = ""

            def detect_signals(text):
                nonlocal current_phase, token_buffer
                token_buffer += text
                # Keep buffer manageable
                if len(token_buffer) > 2000:
                    token_buffer = token_buffer[-1000:]

                # Detect phase changes
                text_lower = text.lower()
                for keyword, phase in PHASE_KEYWORDS.items():
                    if keyword in text_lower and phase != current_phase:
                        current_phase = phase
                        post_to_connection(api_url, connection_id, {
                            "type": "phase_update",
                            "sessionId": runtime_session_id,
                            "payload": {"phase": phase},
                        })
                        break

                # Detect agent switches
                for pattern, agent_name in AGENT_PATTERNS.items():
                    if pattern in text:
                        post_to_connection(api_url, connection_id, {
                            "type": "agent_switch",
                            "sessionId": runtime_session_id,
                            "payload": {"agent": agent_name},
                        })
                        break

            chunk_count = 0

            if "text/event-stream" in content_type:
                # Collect raw bytes first, then decode to avoid splitting
                # multi-byte UTF-8 characters across chunk boundaries.
                raw_parts = []
                for line in response["response"].iter_lines(chunk_size=4096):
                    if line:
                        raw_parts.append(line if isinstance(line, bytes) else line.encode("utf-8"))
                full_text = b"\\n".join(raw_parts).decode("utf-8", errors="replace")
                for ln in full_text.split("\\n"):
                    decoded = ln.strip()
                    if decoded.startswith("data: "):
                        decoded = decoded[6:]
                    if decoded:
                        send_token(decoded, done=False)
                        detect_signals(decoded)
                        chunk_count += 1
            elif content_type == "application/json":
                chunks = []
                for chunk in response.get("response", []):
                    text = chunk.decode("utf-8") if isinstance(chunk, bytes) else chunk
                    chunks.append(text)
                resp_body = "".join(chunks)
                try:
                    parsed = json.loads(resp_body)
                    agent_reply = parsed.get("result", parsed.get("response", resp_body))
                except (json.JSONDecodeError, TypeError):
                    agent_reply = resp_body
                send_token(agent_reply, done=False)
                detect_signals(agent_reply)
                chunk_count += 1
            else:
                resp_body = response.get("response", b"")
                if hasattr(resp_body, "read"):
                    resp_body = resp_body.read()
                if isinstance(resp_body, bytes):
                    resp_body = resp_body.decode("utf-8")
                try:
                    parsed = json.loads(resp_body)
                    agent_reply = parsed.get("result", parsed.get("response", resp_body))
                except (json.JSONDecodeError, TypeError):
                    agent_reply = resp_body
                send_token(agent_reply, done=False)
                detect_signals(agent_reply)
                chunk_count += 1

            # Send final done signal
            send_token("", done=True)
            logger.info(f"Streamed {chunk_count} chunks to connection {connection_id}")

            return {"statusCode": 200, "body": "OK"}
        except Exception as e:
            error_type = type(e).__name__
            logger.error(f"Error invoking orchestrator [{error_type}]")
            # Return generic error to client — do not expose internal details
            post_to_connection(api_url, connection_id, {
                "type": "error",
                "data": f"Error: {error_type} - Agent invocation failed",
            })
            return {"statusCode": 500, "body": "Agent invocation failed"}
    return {"statusCode": 400, "body": "Unknown route"}
`),
      role: handlerRole,
      timeout: cdk.Duration.minutes(5),
      memorySize: 256,
      logGroup: props.logGroup,
      environment: {
        ORCHESTRATOR_AGENT_ARN: process.env.ORCHESTRATOR_AGENT_ARN || "arn:aws:bedrock-agentcore:us-east-1:058264253938:runtime/orchestrator_agent-1YfV9m46l5",
      },
    });

    // WebSocket API
    const api = new apigatewayv2.CfnApi(this, "WebSocketApi", {
      name: "disruptionai-websocket",
      protocolType: "WEBSOCKET",
      routeSelectionExpression: "$request.body.action",
    });

    this.apiId = api.ref;

    // Lambda integration
    const integration = new apigatewayv2.CfnIntegration(
      this,
      "LambdaIntegration",
      {
        apiId: api.ref,
        integrationType: "AWS_PROXY",
        integrationUri: `arn:aws:apigateway:${this.region}:lambda:path/2015-03-31/functions/${handler.functionArn}/invocations`,
      }
    );

    // Routes — IAM authorization on $connect only (API Gateway WebSocket limitation)
    const routeKeys = ["$connect", "$disconnect", "sendMessage"];
    const routeResources: apigatewayv2.CfnRoute[] = [];
    for (const routeKey of routeKeys) {
      const route = new apigatewayv2.CfnRoute(this, `Route-${routeKey.replace("$", "")}`, {
        apiId: api.ref,
        routeKey,
        target: `integrations/${integration.ref}`,
        // WebSocket API only supports auth on $connect
        ...(routeKey === "$connect" ? { authorizationType: "AWS_IAM" } : {}),
      });
      routeResources.push(route);
    }

    // Lambda invoke permission for API Gateway
    handler.addPermission("ApiGatewayInvoke", {
      principal: new iam.ServicePrincipal("apigateway.amazonaws.com"),
      sourceArn: `arn:aws:execute-api:${this.region}:${this.account}:${api.ref}/*`,
    });

    // Allow Lambda to post back to connections
    handlerRole.addToPolicy(
      new iam.PolicyStatement({
        actions: ["execute-api:ManageConnections"],
        resources: [
          `arn:aws:execute-api:${this.region}:${this.account}:${api.ref}/*`,
        ],
      })
    );

    // Stage deployment
    const deployment = new apigatewayv2.CfnDeployment(this, "Deployment", {
      apiId: api.ref,
    });
    // Ensure ALL routes and integration exist before deployment
    deployment.addDependency(integration);
    for (const route of routeResources) {
      deployment.addDependency(route);
    }

    const stage = new apigatewayv2.CfnStage(this, "ProdStage", {
      apiId: api.ref,
      stageName: "prod",
      deploymentId: deployment.ref,
      defaultRouteSettings: {
        loggingLevel: "INFO",
        throttlingBurstLimit: 100,
        throttlingRateLimit: 50,
      },
    });

    this.websocketUrl = `wss://${api.ref}.execute-api.${this.region}.amazonaws.com/prod`;

    new cdk.CfnOutput(this, "WebSocketUrl", {
      value: this.websocketUrl,
      exportName: "disruptionai-websocket-url",
    });

    new cdk.CfnOutput(this, "WebSocketApiId", {
      value: api.ref,
      exportName: "disruptionai-websocket-api-id",
    });
  }
}
