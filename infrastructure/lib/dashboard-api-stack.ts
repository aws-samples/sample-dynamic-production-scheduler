import * as cdk from "aws-cdk-lib";
import * as lambda from "aws-cdk-lib/aws-lambda";
import * as iam from "aws-cdk-lib/aws-iam";
import * as logs from "aws-cdk-lib/aws-logs";
import { Construct } from "constructs";

export interface DashboardApiStackProps extends cdk.StackProps {
  logGroup: logs.ILogGroup;
  authenticatedRoleArn: string;
}

export class DashboardApiStack extends cdk.Stack {
  public readonly functionUrl: string;

  constructor(scope: Construct, id: string, props: DashboardApiStackProps) {
    super(scope, id, props);

    const role = new iam.Role(this, "HandlerRole", {
      roleName: "disruptionai-dashboard-api-role",
      assumedBy: new iam.ServicePrincipal("lambda.amazonaws.com"),
    });

    role.addToPolicy(
      new iam.PolicyStatement({
        actions: ["logs:CreateLogStream", "logs:PutLogEvents"],
        resources: [props.logGroup.logGroupArn + ":*"],
      })
    );

    // DynamoDB read access to all tables
    role.addToPolicy(
      new iam.PolicyStatement({
        actions: [
          "dynamodb:GetItem",
          "dynamodb:Query",
          "dynamodb:Scan",
        ],
        resources: [
          `arn:aws:dynamodb:${this.region}:${this.account}:table/disruptionai-orders`,
          `arn:aws:dynamodb:${this.region}:${this.account}:table/disruptionai-orders/index/*`,
          `arn:aws:dynamodb:${this.region}:${this.account}:table/disruptionai-capacity`,
          `arn:aws:dynamodb:${this.region}:${this.account}:table/disruptionai-manpower`,
          `arn:aws:dynamodb:${this.region}:${this.account}:table/disruptionai-materials`,
          `arn:aws:dynamodb:${this.region}:${this.account}:table/disruptionai-customers`,
        ],
      })
    );

    const handler = new lambda.Function(this, "DashboardApiHandler", {
      functionName: "disruptionai-dashboard-api",
      runtime: lambda.Runtime.PYTHON_3_11,
      handler: "index.handler",
      code: lambda.Code.fromInline(`
import json
import logging
import boto3
from decimal import Decimal
from boto3.dynamodb.conditions import Key

logger = logging.getLogger()
logger.setLevel(logging.INFO)

REGION = "us-east-1"
ddb = boto3.resource("dynamodb", region_name=REGION)

ORDERS_TABLE = "disruptionai-orders"
CAPACITY_TABLE = "disruptionai-capacity"
WORKFORCE_TABLE = "disruptionai-manpower"
MATERIALS_TABLE = "disruptionai-materials"
CUSTOMERS_TABLE = "disruptionai-customers"

class DecimalEncoder(json.JSONEncoder):
    def default(self, o):
        if isinstance(o, Decimal):
            return float(o) if o % 1 else int(o)
        return super().default(o)

def handler(event, context):
    headers = {"Content-Type": "application/json"}

    try:
        body = json.loads(event.get("body", "{}"))
    except Exception:
        body = {}

    plant = body.get("plant", "")
    if not plant or plant not in ("Florida", "Ohio"):
        return {"statusCode": 400, "headers": headers,
                "body": json.dumps({"error": "plant must be Florida or Ohio"})}

    try:
        # Orders via GSI
        orders_table = ddb.Table(ORDERS_TABLE)
        orders_resp = orders_table.query(
            IndexName="plant-status-index",
            KeyConditionExpression=Key("plant").eq(plant),
        )
        orders = orders_resp.get("Items", [])

        # Capacity (scan + filter — small table)
        cap_table = ddb.Table(CAPACITY_TABLE)
        cap_resp = cap_table.scan()
        machines = [i for i in cap_resp.get("Items", []) if i.get("plant") == plant]

        # Workforce
        mp_table = ddb.Table(WORKFORCE_TABLE)
        mp_resp = mp_table.get_item(Key={"plant": plant})
        workforce = mp_resp.get("Item")

        # Materials (scan + filter — small table)
        mat_table = ddb.Table(MATERIALS_TABLE)
        mat_resp = mat_table.scan()
        materials = [i for i in mat_resp.get("Items", []) if i.get("plant") == plant]

        # Customers (all — shared across plants)
        cust_table = ddb.Table(CUSTOMERS_TABLE)
        cust_resp = cust_table.scan()
        customers = {c["customer_id"]: c for c in cust_resp.get("Items", [])}

        # Enrich orders with customer names
        for o in orders:
            cid = o.get("customer_id", "")
            cust = customers.get(cid, {})
            o["customer_name"] = cust.get("customer_name", "Unknown")
            o["customer_tier"] = cust.get("customer_tier", "Tier3")

        result = {
            "plant": plant,
            "orders": orders,
            "machines": machines,
            "workforce": workforce,
            "materials": materials,
        }

        logger.info(f"Dashboard data: plant={plant}, orders={len(orders)}, machines={len(machines)}")
        return {"statusCode": 200, "headers": headers,
                "body": json.dumps(result, cls=DecimalEncoder)}

    except Exception as e:
        logger.error(f"Dashboard API error: {type(e).__name__}")
        return {"statusCode": 500, "headers": headers,
                "body": json.dumps({"error": "Internal server error"})}
`),
      role,
      timeout: cdk.Duration.seconds(15),
      memorySize: 128,
      logGroup: props.logGroup,
    });

    const fnUrl = handler.addFunctionUrl({
      authType: lambda.FunctionUrlAuthType.AWS_IAM,
      cors: {
        allowedOrigins: ["*"], // Acceptable: Function URL uses AWS_IAM auth (SigV4 prevents unauthorized access)
        allowedMethods: [lambda.HttpMethod.POST],
        allowedHeaders: [
          "Content-Type",
          "Authorization",
          "X-Amz-Date",
          "X-Amz-Security-Token",
          "X-Amz-Content-Sha256",
        ],
      },
    });

    // Resource-based policy: allow the Cognito auth role to invoke this Lambda URL
    handler.addPermission("CognitoAuthInvokeUrl", {
      principal: new iam.ArnPrincipal(props.authenticatedRoleArn),
      action: "lambda:InvokeFunctionUrl",
      functionUrlAuthType: lambda.FunctionUrlAuthType.AWS_IAM,
    });
    handler.addPermission("CognitoAuthInvoke", {
      principal: new iam.ArnPrincipal(props.authenticatedRoleArn),
      action: "lambda:InvokeFunction",
    });

    // Identity-based policy: allow the Cognito auth role to call this Lambda
    const authRole = iam.Role.fromRoleArn(this, "CognitoAuthRole", props.authenticatedRoleArn, {
      mutable: true,
    });
    authRole.addToPrincipalPolicy(new iam.PolicyStatement({
      actions: ["lambda:InvokeFunctionUrl", "lambda:InvokeFunction"],
      resources: [handler.functionArn],
    }));

    this.functionUrl = fnUrl.url;

    new cdk.CfnOutput(this, "DashboardApiUrl", {
      value: fnUrl.url,
      exportName: "disruptionai-dashboard-api-url",
    });
  }
}
