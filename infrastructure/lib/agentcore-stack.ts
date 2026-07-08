import * as cdk from "aws-cdk-lib";
import * as iam from "aws-cdk-lib/aws-iam";
import * as agentcore from "@aws-cdk/aws-bedrock-agentcore-alpha";
import { Construct } from "constructs";
import * as path from "path";

export interface AgentCoreStackProps extends cdk.StackProps {
  /** Gateway URL for MCP tool access */
  gatewayUrl?: string;
  /** Cognito token endpoint for OAuth2 */
  cognitoTokenEndpoint?: string;
  /** Cognito app client ID */
  cognitoClientId?: string;
  /** Cognito app client secret */
  cognitoClientSecret?: string;
}

export class AgentCoreStack extends cdk.Stack {
  public readonly orchestratorRuntimeArn: string;

  constructor(scope: Construct, id: string, props: AgentCoreStackProps) {
    super(scope, id, props);

    // Shared env vars for all agents (gateway + cognito credentials)
    const sharedEnv: Record<string, string> = {};
    if (props.gatewayUrl) sharedEnv.GATEWAY_URL = props.gatewayUrl;
    if (props.cognitoTokenEndpoint) sharedEnv.COGNITO_TOKEN_ENDPOINT = props.cognitoTokenEndpoint;
    if (props.cognitoClientId) sharedEnv.COGNITO_CLIENT_ID = props.cognitoClientId;
    if (props.cognitoClientSecret) sharedEnv.COGNITO_CLIENT_SECRET = props.cognitoClientSecret;

    // --- Memory resources ---
    const orchestratorMemory = new agentcore.Memory(this, "OrchestratorMemory", {
      memoryName: "orchestrator_agent_memory",
      description: "Orchestrator agent session memory",
      expirationDuration: cdk.Duration.days(30),
    });

    const impactMemory = new agentcore.Memory(this, "ImpactMemory", {
      memoryName: "impact_assessment_agent_memory",
      description: "Impact assessment agent session memory",
      expirationDuration: cdk.Duration.days(30),
    });

    const capacityMemory = new agentcore.Memory(this, "CapacityMemory", {
      memoryName: "capacity_optimization_agent_memory",
      description: "Capacity optimization agent session memory",
      expirationDuration: cdk.Duration.days(30),
    });

    const constraintMemory = new agentcore.Memory(this, "ConstraintMemory", {
      memoryName: "constraint_matching_agent_memory",
      description: "Constraint matching agent session memory",
      expirationDuration: cdk.Duration.days(30),
    });

    // --- Impact Assessment Agent ---
    const impactRuntime = new agentcore.Runtime(this, "ImpactAssessmentRuntime", {
      runtimeName: "impact_assessment_agent",
      description: "Scores disruption severity across orders",
      agentRuntimeArtifact: agentcore.AgentRuntimeArtifact.fromCodeAsset({
        path: path.join(__dirname, "../../impact-assessment-agent"),
        runtime: agentcore.AgentCoreRuntime.PYTHON_3_13,
        entrypoint: ["src/impact_assessment_agent/agentcore_server.py"],
      }),
      environmentVariables: {
        ...sharedEnv,
        AGENTCORE_MEMORY_ID: impactMemory.memoryId,
      },
    });

    // --- Capacity Optimization Agent ---
    const capacityRuntime = new agentcore.Runtime(this, "CapacityOptimizationRuntime", {
      runtimeName: "capacity_optimization_agent",
      description: "Identifies delay candidates and capacity reallocation",
      agentRuntimeArtifact: agentcore.AgentRuntimeArtifact.fromCodeAsset({
        path: path.join(__dirname, "../../capacity-optimization-agent"),
        runtime: agentcore.AgentCoreRuntime.PYTHON_3_13,
        entrypoint: ["src/capacity_optimization_agent/agentcore_server.py"],
      }),
      environmentVariables: {
        ...sharedEnv,
        AGENTCORE_MEMORY_ID: capacityMemory.memoryId,
      },
    });

    // --- Constraint Matching Agent ---
    const constraintRuntime = new agentcore.Runtime(this, "ConstraintMatchingRuntime", {
      runtimeName: "constraint_matching_agent",
      description: "Runs constraint funnel for order rerouting feasibility",
      agentRuntimeArtifact: agentcore.AgentRuntimeArtifact.fromCodeAsset({
        path: path.join(__dirname, "../../constraint-matching-agent"),
        runtime: agentcore.AgentCoreRuntime.PYTHON_3_13,
        entrypoint: ["src/constraint_matching_agent/agentcore_server.py"],
      }),
      environmentVariables: {
        ...sharedEnv,
        AGENTCORE_MEMORY_ID: constraintMemory.memoryId,
      },
    });

    // --- Orchestrator Agent (depends on sub-agent ARNs) ---
    const orchestratorRuntime = new agentcore.Runtime(this, "OrchestratorRuntime", {
      runtimeName: "orchestrator_agent",
      description: "Coordinates multi-step disruption response workflow",
      agentRuntimeArtifact: agentcore.AgentRuntimeArtifact.fromCodeAsset({
        path: path.join(__dirname, "../../orchestrator-agent"),
        runtime: agentcore.AgentCoreRuntime.PYTHON_3_13,
        entrypoint: ["src/orchestrator_agent/agentcore_server.py"],
      }),
      environmentVariables: {
        ...sharedEnv,
        AGENTCORE_MEMORY_ID: orchestratorMemory.memoryId,
        IMPACT_ASSESSMENT_AGENT_ARN: impactRuntime.agentRuntimeArn,
        CAPACITY_OPTIMIZATION_AGENT_ARN: capacityRuntime.agentRuntimeArn,
        CONSTRAINT_MATCHING_AGENT_ARN: constraintRuntime.agentRuntimeArn,
      },
    });

    // Grant orchestrator permission to invoke sub-agents
    impactRuntime.grantInvoke(orchestratorRuntime);
    capacityRuntime.grantInvoke(orchestratorRuntime);
    constraintRuntime.grantInvoke(orchestratorRuntime);

    // Grant all runtimes permission to invoke Bedrock models
    const bedrockModelPolicy = new iam.PolicyStatement({
      actions: ["bedrock:InvokeModel", "bedrock:InvokeModelWithResponseStream"],
      resources: [
        "arn:aws:bedrock:*::foundation-model/*",
        `arn:aws:bedrock:*:${this.account}:inference-profile/*`,
      ],
    });
    for (const rt of [orchestratorRuntime, impactRuntime, capacityRuntime, constraintRuntime]) {
      rt.addToRolePolicy(bedrockModelPolicy);
    }

    // Grant all runtimes permission to invoke the gateway (scoped to specific gateway)
    const gatewayPolicy = new iam.PolicyStatement({
      actions: ["bedrock-agentcore:InvokeGateway"],
      resources: [`arn:aws:bedrock-agentcore:${this.region}:${this.account}:gateway/disruptionai-*`],
    });
    for (const rt of [orchestratorRuntime, impactRuntime, capacityRuntime, constraintRuntime]) {
      rt.addToRolePolicy(gatewayPolicy);
    }

    // Grant DynamoDB access to orchestrator (for workflow state persistence)
    orchestratorRuntime.addToRolePolicy(
      new iam.PolicyStatement({
        actions: ["dynamodb:GetItem", "dynamodb:PutItem", "dynamodb:UpdateItem", "dynamodb:Query", "dynamodb:Scan"],
        resources: [
          `arn:aws:dynamodb:${this.region}:${this.account}:table/disruptionai-tracker`,
          `arn:aws:dynamodb:${this.region}:${this.account}:table/disruptionai-workflow-state`,
          `arn:aws:dynamodb:${this.region}:${this.account}:table/disruptionai-orders`,
          `arn:aws:dynamodb:${this.region}:${this.account}:table/disruptionai-orders/index/*`,
          `arn:aws:dynamodb:${this.region}:${this.account}:table/disruptionai-capacity`,
          `arn:aws:dynamodb:${this.region}:${this.account}:table/disruptionai-manpower`,
          `arn:aws:dynamodb:${this.region}:${this.account}:table/disruptionai-materials`,
          `arn:aws:dynamodb:${this.region}:${this.account}:table/disruptionai-customers`,
          `arn:aws:dynamodb:${this.region}:${this.account}:table/disruptionai-transfers`,
          `arn:aws:dynamodb:${this.region}:${this.account}:table/disruptionai-transfers/index/*`,
        ],
      }),
    );

    // Export ARNs
    this.orchestratorRuntimeArn = orchestratorRuntime.agentRuntimeArn;

    new cdk.CfnOutput(this, "OrchestratorArn", {
      value: orchestratorRuntime.agentRuntimeArn,
      exportName: "disruptionai-orchestrator-arn",
    });
    new cdk.CfnOutput(this, "ImpactAssessmentArn", {
      value: impactRuntime.agentRuntimeArn,
      exportName: "disruptionai-impact-assessment-arn",
    });
    new cdk.CfnOutput(this, "CapacityOptimizationArn", {
      value: capacityRuntime.agentRuntimeArn,
      exportName: "disruptionai-capacity-optimization-arn",
    });
    new cdk.CfnOutput(this, "ConstraintMatchingArn", {
      value: constraintRuntime.agentRuntimeArn,
      exportName: "disruptionai-constraint-matching-arn",
    });
  }
}
