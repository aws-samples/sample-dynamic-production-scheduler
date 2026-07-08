# DisruptionAI — Multi-Agent Supply Chain Disruption Response System

> **⚠️ Important:** This project is a sample/demo application intended for educational and demonstration purposes only. It is **not intended for production use** without additional security review, testing, and hardening. The IAM policies, authentication configurations, and infrastructure patterns shown here are simplified for clarity and may not meet production security requirements.

DisruptionAI is an AI-powered supply chain disruption management platform built on AWS Bedrock AgentCore. It uses a multi-agent architecture to assess disruption impacts, optimize capacity, match constraints, and orchestrate human-in-the-loop decision workflows — all through a React chat interface.

## Architecture

![DisruptionAI Architecture](docs/DisruptionAI.png)

The platform runs entirely on AWS with 11 CDK-managed stacks:

- Users access the React SPA via CloudFront + S3
- Authentication via Cognito User Pool + Identity Pool (SigV4-signed requests)
- Lambda Function URL serves as the REST proxy to Bedrock AgentCore
- Orchestrator Agent coordinates 3 sub-agents (Impact Assessment, Capacity Optimization, Constraint Matching) running in parallel on AgentCore Runtime
- Agents access ERP data and audit logging through an MCP Gateway with Cognito M2M OAuth2 auth
- MCP Gateway routes tool calls to Lambda functions backed by DynamoDB
- All infrastructure is defined as code — `cdk deploy --all` deploys everything

### Components

| Component | Path | Description |
|---|---|---|
| Orchestrator Agent | `orchestrator-agent/` | Coordinates multi-step disruption response workflow |
| Impact Assessment Agent | `impact-assessment-agent/` | Scores disruption severity across orders |
| Capacity Optimization Agent | `capacity-optimization-agent/` | Identifies delay candidates and capacity reallocation |
| Constraint Matching Agent | `constraint-matching-agent/` | Runs constraint funnel for order rerouting feasibility |
| ERP Data MCP Server | `erp-data-mcp/` | Lambda-based MCP server exposing ERP data tools |
| Audit MCP Server | `audit-mcp/` | Lambda-based MCP server for audit trail logging |
| Frontend SPA | `frontend-spa/` | React + TypeScript + Tailwind chat UI |
| Infrastructure | `infrastructure/` | CDK stacks (9 stacks) |

## Prerequisites

- AWS account with Bedrock AgentCore access (us-east-1)
- AWS CLI v2 configured with credentials
- Python 3.13
- Node.js 22+ and npm
- AWS CDK 2.x
- `bedrock-agentcore-starter-toolkit` (for agent deployments)

## CI/CD Pipeline (GitLab)

The project uses a GitLab CI/CD pipeline (`.gitlab-ci.yml`) that automates the full build and deploy cycle. Merging to `main` triggers the complete pipeline.

### Pipeline Stages

```
build (parallel, runs on MRs + main)
  ├── build:frontend        — npm ci + npm run build (React SPA)
  └── build:mcp-lambdas     — Bundle ERP Data + Audit MCP Lambda packages

deploy (main branch only, sequential)
  ├── deploy:infrastructure — CDK deploy --all (9 stacks)
  ├── deploy:agents:*       — 4 agents via agentcore deploy (parallel, after infra)
  └── deploy:frontend       — S3 sync + CloudFront invalidation (after all agents)
```

### How It Works

1. Push to a branch and open a Merge Request — `build:frontend` and `build:mcp-lambdas` run to validate compilation
2. Merge to `main` — the full pipeline runs: build → deploy infra → deploy agents → deploy frontend
3. Agent deploys use `bedrock-agentcore-starter-toolkit` with `agentcore configure` + `agentcore deploy`
4. Frontend deploy auto-discovers the S3 bucket and CloudFront distribution by account ID

### Pipeline Configuration

- IAM Role: `arn:aws:iam::210490146110:role/GitLab` (assumed by all jobs)
- Region: `us-east-1`
- Python: 3.13 (agents, MCP Lambdas, AWS CLI)
- Node: 22 (frontend, CDK)

## Infrastructure (CDK)

The CDK stacks are in `infrastructure/`. Deploy locally with:

```bash
cd infrastructure
npm install
npx cdk bootstrap   # first time only
npx cdk deploy --all --require-approval never
```

### CDK Stacks

| Stack | File | Purpose |
|---|---|---|
| Database | `lib/database-stack.ts` | DynamoDB tables (orders, capacity, workforce, materials, customers, transfers, workflow-state, tracker) |
| Monitoring | `lib/monitoring-stack.ts` | CloudWatch log groups |
| IAM | `lib/iam-stack.ts` | Agent execution roles and policies |
| Cognito | `lib/cognito-stack.ts` | User Pool, Identity Pool, OAuth2 app clients |
| MCP Lambda | `lib/mcp-lambda-stack.ts` | ERP Data + Audit Lambda functions |
| Gateway IAM | `lib/gateway-iam-stack.ts` | MCP Gateway IAM permissions |
| WebSocket | `lib/websocket-stack.ts` | WebSocket API Gateway |
| REST Proxy | `lib/rest-proxy-stack.ts` | Lambda Function URL (Python 3.13, AWS_IAM auth) |
| Frontend | `lib/frontend-stack.ts` | S3 bucket + CloudFront distribution with security headers |

## Agent Deployment

Agents are deployed to Bedrock AgentCore via the `bedrock-agentcore-starter-toolkit`:

```bash
cd orchestrator-agent
agentcore configure --entrypoint src/orchestrator_agent/agent.py --non-interactive
agentcore deploy --auto-update-on-conflict
```

Repeat for each agent directory. The CI/CD pipeline handles this automatically on merge to main.

## Frontend

```bash
cd frontend-spa
npm install
npm run build
```

### Local Development

```bash
cd frontend-spa
npm install
npm run dev   # runs at http://localhost:5173
```

Configure `frontend-spa/public/config.json` with your deployed backend values (User Pool ID, Identity Pool ID, API URL, etc.).

## Testing

### Unit Tests

```bash
# Frontend
cd frontend-spa && npm test

# Python agents
cd erp-data-mcp && python3 -m pytest tests/ -v
cd capacity-optimization-agent && python3 -m pytest tests/ -v
cd constraint-matching-agent && python3 -m pytest tests/ -v
cd impact-assessment-agent && python3 -m pytest tests/ -v
cd orchestrator-agent && python3 -m pytest tests/ -v
```

### E2E Tests

```bash
python3 test_full_workflow_e2e.py
python3 test_memory_e2e.py
cd infrastructure/scripts && python3 test_gateway_e2e.py
```

## Project Structure

```
disruptionai/
├── orchestrator-agent/          # Orchestrator agent (Strands SDK)
├── impact-assessment-agent/     # Impact scoring agent
├── capacity-optimization-agent/ # Capacity optimization agent
├── constraint-matching-agent/   # Constraint funnel agent
├── erp-data-mcp/                # ERP Data MCP server (Lambda)
├── audit-mcp/                   # Audit MCP server (Lambda)
├── frontend-spa/                # React + TypeScript + Tailwind UI
├── infrastructure/              # CDK stacks
│   ├── bin/app.ts               # CDK app entry point
│   ├── lib/                     # Stack definitions
│   ├── scripts/                 # Setup and utility scripts
│   └── streaming-proxy/         # Lambda streaming proxy (Node.js)
├── .gitlab-ci.yml               # CI/CD pipeline
├── .bedrock_agentcore.yaml      # AgentCore configuration
├── aidlc-docs/                  # Design documentation
└── test_*.py                    # E2E test scripts
```

## Key Design Decisions

- All agents use Strands Agents SDK with Bedrock AgentCore Runtime
- MCP servers run as Lambda functions behind AgentCore Gateway (not direct runtimes)
- OAuth2 (Cognito client credentials) secures Gateway access
- Lambda Function URL with AWS_IAM auth (SigV4 signed from browser via Cognito Identity Pool)
- Python 3.13 runtime for REST proxy Lambda (boto3 included natively, no layer needed)
- AgentCore Memory enabled on all 4 agents for session continuity
- Orchestrator uses `invoke_agent_runtime` to call sub-agents
- Frontend parses orchestrator responses to populate dashboard, disruption views, and transfer workflows
- CI/CD via GitLab with automatic build validation on MRs and full deploy on main merge
