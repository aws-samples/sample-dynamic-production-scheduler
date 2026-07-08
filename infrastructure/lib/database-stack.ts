import * as cdk from "aws-cdk-lib";
import * as dynamodb from "aws-cdk-lib/aws-dynamodb";
import { Construct } from "constructs";

export interface TableArns {
  orders: string;
  ordersIndex: string;
  capacity: string;
  workforce: string;
  materials: string;
  customers: string;
  tracker: string;
  audit: string;
  auditIndex: string;
  transfers: string;
  transfersIndex: string;
  workflowState: string;
}

export class DatabaseStack extends cdk.Stack {
  public readonly tableArns: TableArns;
  public readonly tableNames: Record<string, string>;

  constructor(scope: Construct, id: string, props?: cdk.StackProps) {
    super(scope, id, props);

    const orders = new dynamodb.Table(this, "OrdersTable", {
      tableName: "disruptionai-orders",
      partitionKey: { name: "order_id", type: dynamodb.AttributeType.STRING },
      billingMode: dynamodb.BillingMode.PAY_PER_REQUEST,
      encryption: dynamodb.TableEncryption.AWS_MANAGED,
      pointInTimeRecovery: true,
      removalPolicy: cdk.RemovalPolicy.DESTROY,
    });

    orders.addGlobalSecondaryIndex({
      indexName: "plant-status-index",
      partitionKey: { name: "plant", type: dynamodb.AttributeType.STRING },
      sortKey: { name: "status", type: dynamodb.AttributeType.STRING },
      projectionType: dynamodb.ProjectionType.ALL,
    });

    const capacity = new dynamodb.Table(this, "CapacityTable", {
      tableName: "disruptionai-capacity",
      partitionKey: { name: "machine_type", type: dynamodb.AttributeType.STRING },
      sortKey: { name: "plant", type: dynamodb.AttributeType.STRING },
      billingMode: dynamodb.BillingMode.PAY_PER_REQUEST,
      encryption: dynamodb.TableEncryption.AWS_MANAGED,
      pointInTimeRecovery: true,
      removalPolicy: cdk.RemovalPolicy.DESTROY,
    });

    const workforce = new dynamodb.Table(this, "ManpowerTable", {
      tableName: "disruptionai-manpower",
      partitionKey: { name: "plant", type: dynamodb.AttributeType.STRING },
      billingMode: dynamodb.BillingMode.PAY_PER_REQUEST,
      encryption: dynamodb.TableEncryption.AWS_MANAGED,
      pointInTimeRecovery: true,
      removalPolicy: cdk.RemovalPolicy.DESTROY,
    });

    const materials = new dynamodb.Table(this, "MaterialsTable", {
      tableName: "disruptionai-materials",
      partitionKey: { name: "material_type", type: dynamodb.AttributeType.STRING },
      sortKey: { name: "plant", type: dynamodb.AttributeType.STRING },
      billingMode: dynamodb.BillingMode.PAY_PER_REQUEST,
      encryption: dynamodb.TableEncryption.AWS_MANAGED,
      pointInTimeRecovery: true,
      removalPolicy: cdk.RemovalPolicy.DESTROY,
    });

    const customers = new dynamodb.Table(this, "CustomersTable", {
      tableName: "disruptionai-customers",
      partitionKey: { name: "customer_id", type: dynamodb.AttributeType.STRING },
      billingMode: dynamodb.BillingMode.PAY_PER_REQUEST,
      encryption: dynamodb.TableEncryption.AWS_MANAGED,
      pointInTimeRecovery: true,
      removalPolicy: cdk.RemovalPolicy.DESTROY,
    });

    const tracker = new dynamodb.Table(this, "TrackerTable", {
      tableName: "disruptionai-tracker",
      partitionKey: { name: "session_id", type: dynamodb.AttributeType.STRING },
      billingMode: dynamodb.BillingMode.PAY_PER_REQUEST,
      encryption: dynamodb.TableEncryption.AWS_MANAGED,
      pointInTimeRecovery: true,
      removalPolicy: cdk.RemovalPolicy.DESTROY,
    });

    const audit = new dynamodb.Table(this, "AuditTable", {
      tableName: "disruptionai-audit",
      partitionKey: { name: "session_id", type: dynamodb.AttributeType.STRING },
      sortKey: { name: "entry_id", type: dynamodb.AttributeType.STRING },
      billingMode: dynamodb.BillingMode.PAY_PER_REQUEST,
      encryption: dynamodb.TableEncryption.AWS_MANAGED,
      pointInTimeRecovery: true,
      removalPolicy: cdk.RemovalPolicy.DESTROY,
    });

    audit.addGlobalSecondaryIndex({
      indexName: "session-agent-index",
      partitionKey: { name: "session_id", type: dynamodb.AttributeType.STRING },
      sortKey: { name: "agent", type: dynamodb.AttributeType.STRING },
      projectionType: dynamodb.ProjectionType.ALL,
    });

    const transfers = new dynamodb.Table(this, "TransfersTable", {
      tableName: "disruptionai-transfers",
      partitionKey: { name: "transfer_id", type: dynamodb.AttributeType.STRING },
      billingMode: dynamodb.BillingMode.PAY_PER_REQUEST,
      encryption: dynamodb.TableEncryption.AWS_MANAGED,
      pointInTimeRecovery: true,
      removalPolicy: cdk.RemovalPolicy.DESTROY,
    });

    transfers.addGlobalSecondaryIndex({
      indexName: "target-plant-index",
      partitionKey: { name: "target_plant", type: dynamodb.AttributeType.STRING },
      sortKey: { name: "created_at", type: dynamodb.AttributeType.STRING },
      projectionType: dynamodb.ProjectionType.ALL,
    });

    transfers.addGlobalSecondaryIndex({
      indexName: "source-plant-index",
      partitionKey: { name: "source_plant", type: dynamodb.AttributeType.STRING },
      sortKey: { name: "created_at", type: dynamodb.AttributeType.STRING },
      projectionType: dynamodb.ProjectionType.ALL,
    });

    // Workflow state — persists structured outputs across Lambda invocations
    const workflowState = new dynamodb.Table(this, "WorkflowStateTable", {
      tableName: "disruptionai-workflow-state",
      partitionKey: { name: "session_id", type: dynamodb.AttributeType.STRING },
      sortKey: { name: "state_key", type: dynamodb.AttributeType.STRING },
      billingMode: dynamodb.BillingMode.PAY_PER_REQUEST,
      encryption: dynamodb.TableEncryption.AWS_MANAGED,
      pointInTimeRecovery: true,
      removalPolicy: cdk.RemovalPolicy.DESTROY,
      timeToLiveAttribute: "ttl",
    });

    // Export table ARNs for IAM stack
    this.tableArns = {
      orders: orders.tableArn,
      ordersIndex: `${orders.tableArn}/index/*`,
      capacity: capacity.tableArn,
      workforce: workforce.tableArn,
      materials: materials.tableArn,
      customers: customers.tableArn,
      tracker: tracker.tableArn,
      audit: audit.tableArn,
      auditIndex: `${audit.tableArn}/index/*`,
      transfers: transfers.tableArn,
      transfersIndex: `${transfers.tableArn}/index/*`,
      workflowState: workflowState.tableArn,
    };

    this.tableNames = {
      orders: orders.tableName,
      capacity: capacity.tableName,
      workforce: workforce.tableName,
      materials: materials.tableName,
      customers: customers.tableName,
      tracker: tracker.tableName,
      audit: audit.tableName,
      transfers: transfers.tableName,
      workflowState: workflowState.tableName,
    };

    // CloudFormation outputs for environment variable injection
    Object.entries(this.tableNames).forEach(([key, name]) => {
      new cdk.CfnOutput(this, `TableName-${key}`, {
        value: name,
        exportName: `disruptionai-table-${key}`,
      });
    });
  }
}
