# Components — DisruptionAI

## Component Overview

DisruptionAI is composed of 4 layers: Agent Layer, Data Access Layer (MCP), Backend Services Layer, and Frontend Layer.

```
+-----------------------------------------------------------------------+
|                        Frontend Layer                                 |
|  +-------------------------------+  +------------------------------+  |
|  |  Chat Interface Component     |  |  Side Panel Component        |  |
|  |  - Message display            |  |  - Approval form             |  |
|  |  - Streaming token render     |  |  - Capacity tracker          |  |
|  |  - Agent attribution badges   |  |  - Audit trail viewer        |  |
|  +-------------------------------+  +------------------------------+  |
+-----------------------------------------------------------------------+
         |                                        ^
         | WebSocket (send user input)            | WebSocket (stream responses)
         v                                        |
+-----------------------------------------------------------------------+
|                     Backend Services Layer                            |
|  +-------------------------------+  +------------------------------+  |
|  |  WebSocket Handler            |  |  Session Manager             |  |
|  |  - Connection management      |  |  - Session lifecycle         |  |
|  |  - Message routing            |  |  - AgentCore Memory client   |  |
|  |  - Streaming relay            |  |  - State checkpointing       |  |
|  +-------------------------------+  +------------------------------+  |
+-----------------------------------------------------------------------+
         |
         | Invokes agents
         v
+-----------------------------------------------------------------------+
|                         Agent Layer                                   |
|  +----------------------------------------------------------------+  |
|  |  Orchestrator Agent                                            |  |
|  |  - Workflow coordination (Round 1 parallel, Round 2 sequential)|  |
|  |  - Planner conversation management                            |  |
|  |  - What-if recalculation routing                              |  |
|  |  - Audit trail logging                                        |  |
|  +----------------------------------------------------------------+  |
|       |                    |                    |                     |
|       v                    v                    v                     |
|  +-----------------+ +-----------------+ +------------------+        |
|  | Impact          | | Capacity and    | | Constraint       |        |
|  | Assessment      | | Optimization    | | Matching         |        |
|  | Agent           | | Agent           | | Agent            |        |
|  | - Prioritize    | | - Equipment     | | - 4-layer funnel |        |
|  | - Classify P1-3 | | - Utilization   | | - Order matching |        |
|  | - Reclassify    | | - Delay cands   | | - Order present  |        |
|  +-----------------+ +-----------------+ +------------------+        |
+-----------------------------------------------------------------------+
         |
         | MCP tool calls (data access)
         v
+-----------------------------------------------------------------------+
|                    Data Access Layer (MCP Servers)                    |
|  +---------------------+ +---------------------+ +--------------+   |
|  | ERP Data MCP Server  | | Weather MCP Server  | | Audit MCP    |   |
|  | - Orders (FL + OH)   | | - Mock tornado API  | | Server       |   |
|  | - Capacity data      | | - Plant correlation  | | - Write log  |   |
|  | - Material inventory | |                     | | - Read log   |   |
|  | - Customer data      | |                     | |              |   |
|  +---------------------+ +---------------------+ +--------------+   |
|       |                         |                       |            |
|       v                         v                       v            |
|  +---------------------+ +---------------------+ +--------------+   |
|  | DynamoDB             | | Mock Weather API    | | DynamoDB /   |   |
|  | (Mock ERP Tables)    | | (In-memory)         | | S3 (Audit)   |   |
|  +---------------------+ +---------------------+ +--------------+   |
+-----------------------------------------------------------------------+
```

---

## Component Definitions

### 1. Orchestrator Agent
- **Purpose**: Central coordinator for the entire disruption response workflow
- **Responsibilities**:
  - Manage Planner conversation (interpret intent, route to appropriate agent)
  - Coordinate Round 1 parallel execution (Impact Assessment + Capacity & Optimization agents)
  - Sequence Round 2 flow (Capacity & Optimization Agent for delays, then Constraint Matching Agent for funnel)
  - Handle what-if recalculations (incremental — re-run only affected agents)
  - Generate plain-language summaries via Bedrock Claude
  - Write all decisions to audit trail
- **Framework**: Strands Agents SDK with Bedrock Claude
- **Communication**: Invokes sub-agents as tool calls; accesses data via MCP tools

### 2. Impact Assessment Agent
- **Purpose**: Evaluate and prioritize Florida production orders
- **Responsibilities**:
  - Query all Florida open orders via MCP ERP Data Server
  - Apply weighted priority algorithm (days-to-due-date, customer tier, order value, machine types)
  - Classify orders as P1 / P2 / P3
  - Explain classification logic in natural language
  - Handle Planner reclassification requests
  - Write prioritized orders to AgentCore Memory shared context
- **Framework**: Strands Agents SDK with Bedrock Claude
- **Orchestration Pattern**: Tool call — invoked by Orchestrator as a tool

### 3. Capacity & Optimization Agent
- **Purpose**: Assess Ohio plant capacity and manage delay optimization
- **Responsibilities**:
  - Query Ohio equipment capability via MCP ERP Data Server
  - Calculate machine utilization across shift types (Normal, Overtime, Weekend)
  - Query manpower headcount and availability
  - Query raw material inventory and surplus
  - Query existing Ohio order load with slack calculations
  - Identify primary bottleneck (Rolling Mill vs Finishing Line)
  - Handle Planner-added constraints with immediate recalculation
  - Identify Ohio delay candidates (P3, deadline > 6 weeks)
  - Calculate freed capacity per delay candidate
  - Process Planner delay approval/rejection decisions
  - Recalculate capacity after approved delays
  - Write capacity snapshot to AgentCore Memory shared context
- **Framework**: Strands Agents SDK with Bedrock Claude
- **Orchestration Pattern**: Tool call — invoked by Orchestrator as a tool

### 4. Constraint Matching Agent
- **Purpose**: Produce rerouting schedule through 4-layer constraint funnel
- **Responsibilities**:
  - Read shared context from AgentCore Memory (prioritized orders + post-delay capacity)
  - Run 4-layer constraint funnel per order (Equipment, Material, Utilization, Cascade)
  - Present orders one at a time for Planner approval
  - Update running capacity tracker in DynamoDB after each decision
  - Handle skip/reorder requests
- **Framework**: Strands Agents SDK with Bedrock Claude
- **Orchestration Pattern**: Tool call — invoked by Orchestrator; interactive with Planner via Orchestrator relay

### 5. ERP Data MCP Server
- **Purpose**: Provide standardized access to mock ERP data in DynamoDB
- **Responsibilities**:
  - Expose tools for querying production orders (Florida and Ohio)
  - Expose tools for querying Ohio capacity (machines, manpower, materials)
  - Expose tools for querying customer data
  - Expose tools for updating order status and priority
  - Expose tools for reading/updating running capacity tracker
- **Technology**: Python MCP server (stdio or SSE transport)
- **Data Store**: DynamoDB tables

### 6. Weather MCP Server
- **Purpose**: Provide mock weather/disruption event data
- **Responsibilities**:
  - Expose tool for checking active weather events by region
  - Correlate weather events with plant locations
- **Technology**: Python MCP server
- **Data Store**: In-memory mock data

### 7. Audit MCP Server
- **Purpose**: Provide standardized audit trail read/write
- **Responsibilities**:
  - Expose tool for writing audit entries (decision, agent, timestamp, rationale)
  - Expose tool for reading audit trail (filtered by session, agent, time range)
- **Technology**: Python MCP server
- **Data Store**: DynamoDB (separate audit table)

### 8. WebSocket Handler
- **Purpose**: Manage WebSocket connections between frontend and backend
- **Responsibilities**:
  - Accept WebSocket connections from React frontend
  - Route incoming messages to Orchestrator Agent
  - Stream agent responses (tokens) back to frontend
  - Handle connection lifecycle (connect, disconnect, reconnect)
- **Technology**: Python (FastAPI or custom WebSocket handler on ECS)

### 9. Session Manager
- **Purpose**: Manage workflow session state
- **Responsibilities**:
  - Create and track workflow sessions
  - Interface with AgentCore Memory for shared agent context
  - Checkpoint key decisions for recovery
- **Technology**: Python service within ECS backend

### 10. Chat Interface Component (Frontend)
- **Purpose**: Primary conversational UI for Planner interaction
- **Responsibilities**:
  - Display streaming agent responses with token-by-token rendering
  - Show agent attribution badges (which agent is active)
  - Render structured data inline (tables, capacity summaries)
  - Provide "Explain reasoning" expandable sections
  - Send Planner messages via WebSocket
- **Technology**: React + TypeScript (Vite)

### 11. Side Panel Component (Frontend)
- **Purpose**: Structured approval and monitoring interface
- **Responsibilities**:
  - Display Approve / Reject / Skip buttons for order decisions
  - Show running capacity tracker (updated after each decision)
  - Display audit trail for review
  - Show workflow phase progress indicator
- **Technology**: React + TypeScript (Vite)
