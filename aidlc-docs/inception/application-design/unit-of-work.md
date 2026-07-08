# Unit of Work Definitions — DisruptionAI

## Decomposition Strategy
- **Granularity**: By agent — each agent and MCP server is an independent unit
- **MCP Packaging**: Separate packages — each MCP server independently deployable
- **Infrastructure**: Full CDK stack
- **Total Units**: 9

## Development Sequence (Data-First)

```
Phase 1 (Data Layer):
  Unit 1: ERP Data MCP Server
  Unit 2: Weather MCP Server
  Unit 3: Audit MCP Server

Phase 2 (Agent Layer):
  Unit 4: Impact Assessment Agent
  Unit 5: Capacity & Optimization Agent
  Unit 6: Constraint Matching Agent
  Unit 7: Orchestrator Agent

Phase 3 (Presentation Layer):
  Unit 8: Frontend (React SPA)

Phase 4 (Infrastructure Layer):
  Unit 9: Infrastructure (CDK)
```

---

## Unit Definitions

### Unit 1: ERP Data MCP Server
- **Type**: Data Access / MCP Server
- **Language**: Python
- **Purpose**: Provide standardized access to mock ERP data in DynamoDB
- **Components**: MCP server with tools for orders, capacity, manpower, materials, customers, running tracker
- **Responsibilities**:
  - DynamoDB table schema definition and seed data
  - MCP tools: get_orders, get_order_by_id, update_order_priority, update_order_status
  - MCP tools: get_machine_capacity, get_manpower, get_materials, get_customers
  - MCP tools: get_running_tracker, update_running_tracker
  - Data validation and error handling
- **Deployment**: Separate Python process (stdio transport), runs as subprocess alongside agents
- **Stories**: Supports US-02, US-03, US-04, US-06, US-07, US-08, US-09

### Unit 2: Weather MCP Server (OPTIONAL)
- **Type**: Data Access / MCP Server
- **Language**: Python
- **Purpose**: Provide mock weather/disruption event data
- **Status**: OPTIONAL — MVP can use manual disruption trigger instead
- **Components**: MCP server with tools for weather events and plant impact
- **Responsibilities**:
  - Mock weather event data (tornado approaching Florida)
  - MCP tools: get_active_events, get_plant_impact
  - Plant-to-region correlation logic
- **Deployment**: Separate Python process (stdio transport)
- **Stories**: Supports US-01 (if implemented; otherwise US-01 uses manual trigger)
- **MVP Alternative**: Planner manually triggers disruption workflow; Orchestrator skips weather check

### Unit 3: Audit MCP Server
- **Type**: Data Access / MCP Server
- **Language**: Python
- **Purpose**: Provide standardized audit trail read/write
- **Components**: MCP server with tools for audit entries
- **Responsibilities**:
  - DynamoDB audit table schema and access
  - MCP tools: write_audit_entry, get_audit_trail
  - Structured audit entry format (session, agent, action, details, timestamp)
- **Deployment**: Separate Python process (stdio transport)
- **Stories**: Supports US-03, US-08

### Unit 4: Impact Assessment Agent
- **Type**: AI Agent
- **Language**: Python (Strands Agents SDK)
- **Purpose**: Evaluate and prioritize Florida production orders
- **Components**: Strands Agent with system prompt, MCP tool bindings, priority algorithm
- **Responsibilities**:
  - Weighted priority algorithm (days-to-due-date, customer tier, order value, machine types)
  - P1/P2/P3 classification with configurable thresholds
  - Natural language explanation of classification logic
  - Planner reclassification handling
  - Write prioritized orders to AgentCore Memory
- **Deployment**: Python module within ECS container, invoked by Orchestrator as tool
- **Stories**: US-02, US-03

### Unit 5: Capacity & Optimization Agent
- **Type**: AI Agent
- **Language**: Python (Strands Agents SDK)
- **Purpose**: Assess Ohio plant capacity and manage delay optimization
- **Components**: Strands Agent with system prompt, MCP tool bindings, capacity calculations, delay logic
- **Responsibilities**:
  - Equipment capability analysis (Rolling Mill, Finishing Line)
  - Machine utilization calculation by shift type
  - Manpower availability assessment
  - Raw material surplus calculation
  - Existing Ohio order load with slack
  - Bottleneck identification
  - Planner constraint handling with recalculation
  - Ohio delay candidate identification (P3, deadline > 6 weeks)
  - Freed capacity calculation per delay candidate
  - Planner delay approval/rejection processing
  - Post-delay capacity recalculation
  - Write capacity snapshot to AgentCore Memory
- **Deployment**: Python module within ECS container, invoked by Orchestrator as tool
- **Stories**: US-04, US-05, US-06

### Unit 6: Constraint Matching Agent
- **Type**: AI Agent
- **Language**: Python (Strands Agents SDK)
- **Purpose**: Produce rerouting schedule through 4-layer constraint funnel
- **Components**: Strands Agent with system prompt, MCP tool bindings, constraint funnel logic
- **Responsibilities**:
  - 4-layer constraint funnel (Equipment, Material, Utilization, Cascade)
  - Order-by-order interactive presentation
  - Running capacity tracker updates
  - Skip/reorder handling
- **Deployment**: Python module within ECS container, invoked by Orchestrator as tool
- **Stories**: US-07, US-08, US-09

### Unit 7: Orchestrator Agent
- **Type**: AI Agent (Coordinator)
- **Language**: Python (Strands Agents SDK)
- **Purpose**: Coordinate entire disruption response workflow
- **Components**: Strands Agent with system prompt, sub-agent tool definitions, workflow logic
- **Responsibilities**:
  - Planner conversation management (intent detection, routing)
  - Round 1 parallel execution (Impact Assessment + Capacity & Optimization agents)
  - Round 2 sequential flow (Capacity & Optimization Agent for delays, Constraint Matching Agent for funnel)
  - What-if recalculation routing (incremental)
  - Plain-language summary generation
  - Audit trail logging via Audit MCP
  - WebSocket streaming integration
  - Session management via AgentCore Memory
- **Deployment**: Python module within ECS container, entry point for agent layer
- **Stories**: US-01, US-05, US-10 (plus coordination for all stories)

### Unit 8: Frontend
- **Type**: Presentation Layer
- **Language**: TypeScript / React (Vite)
- **Purpose**: Conversational UI with structured approval interface
- **Components**: Chat Interface, Side Panel, WebSocket client
- **Responsibilities**:
  - Chat Interface: streaming token display, agent badges, inline tables, expandable reasoning
  - Side Panel: Approve/Reject/Skip buttons, running capacity tracker, audit trail viewer, phase progress
  - WebSocket client: connection management, message send/receive, reconnection
  - UI state management for approval flow
- **Deployment**: Static SPA on S3 + CloudFront
- **Stories**: US-08, US-10

### Unit 9: Infrastructure
- **Type**: Infrastructure as Code
- **Language**: TypeScript (AWS CDK)
- **Purpose**: Full AWS infrastructure provisioning
- **Components**: CDK stacks for all AWS resources
- **Responsibilities**:
  - VPC with public/private subnets
  - ECS/Fargate cluster and task definitions
  - API Gateway WebSocket API
  - DynamoDB tables (ERP data + audit)
  - S3 bucket for frontend hosting
  - CloudFront distribution
  - IAM roles and policies (least-privilege)
  - CloudWatch log groups, alarms, dashboards
  - Security groups and network ACLs
- **Deployment**: CDK deploy
- **Stories**: Supports all stories (infrastructure foundation)
