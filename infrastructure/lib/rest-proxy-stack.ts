import * as cdk from "aws-cdk-lib";
import * as lambda from "aws-cdk-lib/aws-lambda";
import * as iam from "aws-cdk-lib/aws-iam";
import * as logs from "aws-cdk-lib/aws-logs";
import { Construct } from "constructs";

export interface RestProxyStackProps extends cdk.StackProps {
  logGroup: logs.ILogGroup;
  authenticatedRoleArn: string;
  /**
   * Allowed CORS origins for the Function URL. Defaults to the
   * ALLOWED_ORIGINS env var (comma-separated) when set. Falls back to "*"
   * only when unset — restrict this to your CloudFront domain in production.
   */
  allowedOrigins?: string[];
}

export class RestProxyStack extends cdk.Stack {
  public readonly functionUrl: string;

  constructor(scope: Construct, id: string, props: RestProxyStackProps) {
    super(scope, id, props);

    const handlerRole = new iam.Role(this, "HandlerRole", {
      roleName: "disruptionai-rest-proxy-role",
      assumedBy: new iam.ServicePrincipal("lambda.amazonaws.com"),
    });

    handlerRole.addToPolicy(
      new iam.PolicyStatement({
        actions: ["logs:CreateLogStream", "logs:PutLogEvents"],
        resources: [props.logGroup.logGroupArn + ":*"],
      })
    );

    // Scoped to orchestrator_agent runtimes only (least privilege) rather than
    // all runtimes in the account. The runtime name carries a generated suffix,
    // so a prefix wildcard is used.
    handlerRole.addToPolicy(
      new iam.PolicyStatement({
        actions: ["bedrock-agentcore:InvokeAgentRuntime"],
        resources: [
          `arn:aws:bedrock-agentcore:${this.region}:${this.account}:runtime/orchestrator_agent-*`,
        ],
      })
    );

    // Least-privilege DynamoDB access, split by operation type.
    // Read-only: orders, capacity, workforce, materials, customers,
    // workflow-state, tracker, and transfers (the proxy queries/scans them).
    handlerRole.addToPolicy(
      new iam.PolicyStatement({
        sid: "DynamoDBReadOnly",
        actions: ["dynamodb:GetItem", "dynamodb:Query", "dynamodb:Scan"],
        resources: [
          `arn:aws:dynamodb:${this.region}:${this.account}:table/disruptionai-orders`,
          `arn:aws:dynamodb:${this.region}:${this.account}:table/disruptionai-orders/index/*`,
          `arn:aws:dynamodb:${this.region}:${this.account}:table/disruptionai-capacity`,
          `arn:aws:dynamodb:${this.region}:${this.account}:table/disruptionai-manpower`,
          `arn:aws:dynamodb:${this.region}:${this.account}:table/disruptionai-materials`,
          `arn:aws:dynamodb:${this.region}:${this.account}:table/disruptionai-customers`,
          `arn:aws:dynamodb:${this.region}:${this.account}:table/disruptionai-workflow-state`,
          `arn:aws:dynamodb:${this.region}:${this.account}:table/disruptionai-tracker`,
          `arn:aws:dynamodb:${this.region}:${this.account}:table/disruptionai-transfers`,
          `arn:aws:dynamodb:${this.region}:${this.account}:table/disruptionai-transfers/index/*`,
        ],
      })
    );

    // Write access: only the transfers table receives PutItem/UpdateItem
    // (transfer_submit and transfer_decide actions).
    handlerRole.addToPolicy(
      new iam.PolicyStatement({
        sid: "DynamoDBTransfersWrite",
        actions: ["dynamodb:PutItem", "dynamodb:UpdateItem"],
        resources: [
          `arn:aws:dynamodb:${this.region}:${this.account}:table/disruptionai-transfers`,
        ],
      })
    );

    // Note: Python 3.13 runtime includes boto3, no layer needed
    const handler = new lambda.Function(this, "RestProxyHandler", {
      functionName: "disruptionai-rest-proxy",
      runtime: lambda.Runtime.PYTHON_3_13,
      handler: "index.handler",
      code: lambda.Code.fromInline(`
import json
import logging
import os
import hashlib
import uuid
import datetime
import boto3
from decimal import Decimal
from botocore.config import Config
from boto3.dynamodb.conditions import Key

logger = logging.getLogger()
logger.setLevel(logging.INFO)

ORCHESTRATOR_AGENT_ARN = os.environ.get("ORCHESTRATOR_AGENT_ARN", "")
REGION = os.environ.get("AWS_REGION", "us-east-1")

agentcore = None
ddb = None

class DecimalEncoder(json.JSONEncoder):
    def default(self, o):
        if isinstance(o, Decimal):
            return float(o) if o % 1 else int(o)
        return super().default(o)

def get_ddb():
    global ddb
    if ddb is None:
        ddb = boto3.resource("dynamodb", region_name=REGION)
    return ddb

def get_client():
    global agentcore
    if agentcore is None:
        cfg = Config(read_timeout=900, connect_timeout=10, retries={"max_attempts": 1})
        agentcore = boto3.client("bedrock-agentcore", region_name=REGION, config=cfg)
    return agentcore

def handler(event, context):
    # CORS is handled by the Function URL configuration — do NOT set
    # Access-Control-Allow-Origin here or the browser will see duplicate
    # headers and reject the response.
    headers = {
        "Content-Type": "application/json",
    }

    try:
        body = json.loads(event.get("body", "{}"))
    except Exception:
        return {"statusCode": 400, "headers": headers, "body": json.dumps({"error": "Invalid JSON"})}

    user_message = body.get("message", "")
    session_id = body.get("sessionId", "")
    plant = body.get("plant", "")
    action = body.get("action", "")
    current_phase = body.get("currentPhase", "")

    # Dashboard data endpoint — direct DynamoDB query, no orchestrator
    if action == "dashboard":
        if not plant or plant not in ("Florida", "Ohio"):
            return {"statusCode": 400, "headers": headers, "body": json.dumps({"error": "plant required"})}
        try:
            d = get_ddb()
            orders_t = d.Table("disruptionai-orders")
            o_resp = orders_t.query(IndexName="plant-status-index", KeyConditionExpression=Key("plant").eq(plant))
            orders = o_resp.get("Items", [])
            cap_t = d.Table("disruptionai-capacity")
            machines = [i for i in cap_t.scan().get("Items", []) if i.get("plant") == plant]
            mp_t = d.Table("disruptionai-manpower")
            workforce = mp_t.get_item(Key={"plant": plant}).get("Item")
            mat_t = d.Table("disruptionai-materials")
            materials = [i for i in mat_t.scan().get("Items", []) if i.get("plant") == plant]
            cust_t = d.Table("disruptionai-customers")
            customers = {c["customer_id"]: c for c in cust_t.scan().get("Items", [])}
            for o in orders:
                cid = o.get("customer_id", "")
                c = customers.get(cid, {})
                o["customer_name"] = c.get("customer_name", "Unknown")
                o["customer_tier"] = c.get("customer_tier", "Tier3")
            result = {"plant": plant, "orders": orders, "machines": machines, "workforce": workforce, "materials": materials}
            # Include transfers — incoming (target_plant=plant) and outgoing (source_plant=plant)
            # If sessionId is provided, filter to just that session's transfers
            tr_t = d.Table("disruptionai-transfers")
            incoming_resp = tr_t.query(IndexName="target-plant-index", KeyConditionExpression=Key("target_plant").eq(plant))
            outgoing_resp = tr_t.query(IndexName="source-plant-index", KeyConditionExpression=Key("source_plant").eq(plant))
            incoming = incoming_resp.get("Items", [])
            outgoing = outgoing_resp.get("Items", [])
            if session_id:
                incoming = [t for t in incoming if t.get("session_id") == session_id]
                outgoing = [t for t in outgoing if t.get("session_id") == session_id]
            result["incomingTransfers"] = incoming
            result["outgoingTransfers"] = outgoing
            return {"statusCode": 200, "headers": headers, "body": json.dumps(result, cls=DecimalEncoder)}
        except Exception as e:
            logger.error(f"Dashboard query failed: {type(e).__name__}")
            return {"statusCode": 500, "headers": headers, "body": json.dumps({"error": "Internal server error"})}

    # Transfer submit — write transfer requests to DynamoDB
    if action == "transfer_submit":
        transfers = body.get("transfers", [])
        source_plant = body.get("source_plant", "")
        target_plant = body.get("target_plant", "")
        if not transfers or not source_plant or not target_plant:
            return {"statusCode": 400, "headers": headers, "body": json.dumps({"error": "transfers, source_plant, target_plant required"})}
        try:
            d = get_ddb()
            t_table = d.Table("disruptionai-transfers")
            now = datetime.datetime.utcnow().isoformat() + "Z"
            ids = []
            for tr in transfers:
                tid = str(uuid.uuid4())
                t_table.put_item(Item={
                    "transfer_id": tid,
                    "order_id": tr.get("orderId", ""),
                    "source_plant": source_plant,
                    "target_plant": target_plant,
                    "status": "submitted_for_review",
                    "session_id": session_id,
                    "order_data": json.loads(json.dumps(tr, cls=DecimalEncoder)),
                    "recommendation": tr.get("recommendation", ""),
                    "reasoning": tr.get("reasoning", ""),
                    "funnel_results": tr.get("funnelResults", []),
                    "created_at": now,
                    "updated_at": now,
                })
                ids.append(tid)
            return {"statusCode": 200, "headers": headers, "body": json.dumps({"transfer_ids": ids})}
        except Exception as e:
            logger.error(f"Transfer submit failed: {type(e).__name__}")
            return {"statusCode": 500, "headers": headers, "body": json.dumps({"error": "Internal server error"})}

    # Transfer list — query transfers for a plant (incoming or outgoing)
    if action == "transfer_list":
        if not plant:
            return {"statusCode": 400, "headers": headers, "body": json.dumps({"error": "plant required"})}
        direction = body.get("direction", "incoming")
        try:
            import datetime as _dt
            d = get_ddb()
            t_table = d.Table("disruptionai-transfers")
            if direction == "incoming":
                resp = t_table.query(IndexName="target-plant-index", KeyConditionExpression=Key("target_plant").eq(plant))
            else:
                resp = t_table.query(IndexName="source-plant-index", KeyConditionExpression=Key("source_plant").eq(plant))
            items = resp.get("Items", [])
            return {"statusCode": 200, "headers": headers, "body": json.dumps({"transfers": items}, cls=DecimalEncoder)}
        except Exception as e:
            logger.error(f"Transfer list failed: {type(e).__name__}")
            return {"statusCode": 500, "headers": headers, "body": json.dumps({"error": "Internal server error"})}

    # Transfer decide — accept or reject a transfer
    if action == "transfer_decide":
        transfer_id = body.get("transfer_id", "")
        decision = body.get("decision", "")
        reason = body.get("reason", "")
        if not transfer_id or decision not in ("approved", "declined"):
            return {"statusCode": 400, "headers": headers, "body": json.dumps({"error": "transfer_id and decision (approved/declined) required"})}
        try:
            import datetime as _dt
            d = get_ddb()
            t_table = d.Table("disruptionai-transfers")
            now = datetime.datetime.utcnow().isoformat() + "Z"
            update_expr = "SET #s = :s, updated_at = :u"
            expr_vals = {":s": decision, ":u": now}
            expr_names = {"#s": "status"}
            if reason:
                update_expr += ", decline_reason = :r"
                expr_vals[":r"] = reason
            t_table.update_item(
                Key={"transfer_id": transfer_id},
                UpdateExpression=update_expr,
                ExpressionAttributeValues=expr_vals,
                ExpressionAttributeNames=expr_names,
            )
            return {"statusCode": 200, "headers": headers, "body": json.dumps({"transfer_id": transfer_id, "status": decision})}
        except Exception as e:
            logger.error(f"Transfer decide failed: {type(e).__name__}")
            return {"statusCode": 500, "headers": headers, "body": json.dumps({"error": "Internal server error"})}

    # Session state endpoint — reads workflow-state + tracker from DynamoDB
    if action == "session_state":
        if not session_id:
            return {"statusCode": 400, "headers": headers, "body": json.dumps({"error": "sessionId required"})}
        try:
            d = get_ddb()
            # Read all workflow-state entries for this session
            ws_table = d.Table("disruptionai-workflow-state")
            ws_resp = ws_table.query(KeyConditionExpression=Key("session_id").eq(session_id))
            ws_items = ws_resp.get("Items", [])
            workflow_state = {}
            for item in ws_items:
                key = item.get("state_key", "")
                data = item.get("data")
                if key and data is not None:
                    workflow_state[key] = data

            # Read tracker for this session
            tracker_table = d.Table("disruptionai-tracker")
            tracker_resp = tracker_table.get_item(Key={"session_id": session_id})
            tracker = tracker_resp.get("Item")

            # Read transfers for this session (scan+filter — low volume)
            transfers_table = d.Table("disruptionai-transfers")
            tr_resp = transfers_table.scan(
                FilterExpression=Key("session_id").eq(session_id),
                ProjectionExpression="transfer_id, order_id, source_plant, target_plant, #s, recommendation, reasoning, created_at, updated_at",
                ExpressionAttributeNames={"#s": "status"},
            )
            transfers = tr_resp.get("Items", [])

            result = {
                "sessionId": session_id,
                "workflowState": workflow_state,
                "tracker": tracker,
                "transfers": transfers,
            }
            return {"statusCode": 200, "headers": headers, "body": json.dumps(result, cls=DecimalEncoder)}
        except Exception as e:
            logger.error(f"Session state query failed: {type(e).__name__}")
            return {"statusCode": 500, "headers": headers, "body": json.dumps({"error": "Internal server error"})}

    if not user_message:
        return {"statusCode": 400, "headers": headers, "body": json.dumps({"error": "No message"})}
    if not ORCHESTRATOR_AGENT_ARN:
        return {"statusCode": 500, "headers": headers, "body": json.dumps({"error": "Orchestrator not configured"})}

    # Derive stable session UUID from sessionId
    # If the frontend sends back a disruptionai-* ID, use it as-is (no re-hash)
    if session_id and session_id.startswith("disruptionai-"):
        runtime_session_id = session_id
    elif session_id:
        session_uuid = str(uuid.UUID(hashlib.sha256(session_id.encode()).hexdigest()[:32]))
        runtime_session_id = f"disruptionai-{session_uuid}"
    else:
        runtime_session_id = f"disruptionai-{uuid.uuid4()}"

    logger.info(f"Invoking orchestrator: session={runtime_session_id}, msg_len={len(user_message)}, plant={plant}")
    client = get_client()

    try:
        response = client.invoke_agent_runtime(
            agentRuntimeArn=ORCHESTRATOR_AGENT_ARN,
            runtimeSessionId=runtime_session_id,
            payload=json.dumps({"prompt": user_message, "session_id": session_id, "plant": plant, "currentPhase": current_phase}),
        )
    except Exception as e:
        logger.error(f"invoke_agent_runtime failed: {type(e).__name__}")
        return {"statusCode": 502, "headers": headers, "body": json.dumps({"error": "Agent invocation failed"})}

    # Read response
    content_type = response.get("contentType", "")
    logger.info(f"Response contentType: {content_type}")

    if "text/event-stream" in content_type:
        raw_parts = []
        for line in response["response"].iter_lines(chunk_size=4096):
            if line:
                raw_parts.append(line if isinstance(line, bytes) else line.encode("utf-8"))
        full_text = b"\\n".join(raw_parts).decode("utf-8", errors="replace")
        parts = []
        for ln in full_text.split("\\n"):
            stripped = ln.strip()
            if stripped.startswith("data: "):
                stripped = stripped[6:]
            if stripped:
                parts.append(stripped)
        resp_body = "".join(parts)
    elif content_type == "application/json":
        chunks = []
        for chunk in response.get("response", []):
            chunks.append(chunk.decode("utf-8") if isinstance(chunk, bytes) else chunk)
        resp_body = "".join(chunks)
    else:
        resp_body = response.get("response", b"")
        if hasattr(resp_body, "read"):
            resp_body = resp_body.read()
        if isinstance(resp_body, bytes):
            resp_body = resp_body.decode("utf-8")

    # Parse agent result
    # The AgentCore entrypoint returns a full dict {result, ui, session_id}
    # which BedrockAgentCoreApp serializes as JSON. The SSE parser joins
    # data: lines — the result should be valid JSON containing all fields.
    try:
        parsed = json.loads(resp_body)
        agent_reply = parsed.get("result", parsed.get("response", resp_body))
        agent_error = parsed.get("error")
        agent_ui = parsed.get("ui", {})
        logger.info(f"Parsed response: result_len={len(str(agent_reply)) if agent_reply else 0}, has_error={bool(agent_error)}, has_ui={bool(agent_ui)}")
    except (json.JSONDecodeError, TypeError):
        agent_reply = resp_body
        agent_error = None
        agent_ui = {}
        logger.info(f"Response not JSON, using raw text (len={len(resp_body)})")

    result = {
        "sessionId": runtime_session_id,
        "message": agent_reply,
        "ui": agent_ui,
        "error": agent_error,
    }
    # Log metadata only — never log agent_reply content as it may contain user data
    logger.info(f"Returning response: len={len(str(agent_reply))}")
    return {"statusCode": 200, "headers": headers, "body": json.dumps(result)}
`),
      role: handlerRole,
      timeout: cdk.Duration.minutes(15),
      memorySize: 256,
      logGroup: props.logGroup,
      environment: {
        ORCHESTRATOR_AGENT_ARN:
          process.env.ORCHESTRATOR_AGENT_ARN ||
          `arn:aws:bedrock-agentcore:us-east-1:${this.account}:runtime/orchestrator_agent-1YfV9m46l5`,
      },
    });

    // Resolve allowed CORS origins. Prefer the explicit prop, then the
    // ALLOWED_ORIGINS env var (comma-separated), and only fall back to "*"
    // when nothing is configured. Restrict to your CloudFront domain in
    // production — "*" lets any site issue (SigV4-signed) cross-origin
    // requests, which broadens CSRF exposure if credentials are leaked.
    // Sourced from config (not the FrontendStack) to avoid a circular
    // dependency, since the frontend already consumes this proxy's URL.
    const allowedOrigins =
      props.allowedOrigins ??
      (process.env.ALLOWED_ORIGINS
        ? process.env.ALLOWED_ORIGINS.split(",").map((o) => o.trim()).filter(Boolean)
        : ["*"]);

    // Lambda Function URL — AWS_IAM auth (SECURITY-08)
    const fnUrl = handler.addFunctionUrl({
      authType: lambda.FunctionUrlAuthType.AWS_IAM,
      cors: {
        allowedOrigins,
        allowedMethods: [lambda.HttpMethod.POST],
        allowedHeaders: [
          "Content-Type",
          "Authorization",
          "X-Amz-Date",
          "X-Amz-Security-Token",
          "X-Amz-Content-Sha256",
        ],
        exposedHeaders: ["X-Session-Id"],
      },
    });

    // Grant Cognito authenticated users permission to invoke the Function URL.
    // AWS requires BOTH lambda:InvokeFunctionUrl AND lambda:InvokeFunction
    // for Function URL invocation with AWS_IAM auth type.
    const authenticatedRole = iam.Role.fromRoleArn(
      this,
      "CognitoAuthRole",
      props.authenticatedRoleArn
    );
    handler.grantInvokeUrl(authenticatedRole);
    handler.grantInvoke(authenticatedRole);

    this.functionUrl = fnUrl.url;

    new cdk.CfnOutput(this, "RestProxyUrl", {
      value: fnUrl.url,
      exportName: "disruptionai-rest-proxy-url",
    });
  }
}
