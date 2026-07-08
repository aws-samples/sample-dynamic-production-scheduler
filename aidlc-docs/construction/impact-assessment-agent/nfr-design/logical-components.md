# Logical Components — Unit 4: Impact Assessment Agent

## Component Overview

```
Orchestrator Agent
      |
      | invoke (Strands tool call)
      v
+---------------------+
| Agent Entry Point   |  (fail-closed wrapper, Pattern 7)
+---------------------+
      |
      v
+---------------------+
| Strands Agent       |  (Claude 4.5 Haiku, system prompt)
+---------------------+
      |
      +-------+-------+
      |               |
      v               v
+-----------+   +-----------+
| MCP Tools |   | Py Tools  |
| (HTTP/SSE)|   | (scoring) |
+-----------+   +-----------+
      |               |
      v               v
+---------------------+
| Logging Layer       |  (JSON structured, Pattern 4)
+---------------------+
      |
      v
+---------------------+
| AgentCore Runtime   |  (hosting, scaling, lifecycle)
+---------------------+
```

---

## Component 1: Agent Entry Point

- **Module**: `agent.py`
- **Responsibility**: Initialize Strands Agent, configure model, register tools, expose invocation interface
- **Pattern**: Fail-Closed Agent Wrapper (Pattern 7)
- **Startup sequence**:
  1. Load AgentSettings from environment
  2. Validate scoring weights (sum = 1.0) and thresholds (p1 > p2)
  3. Configure structured logging
  4. Initialize BedrockModel (Claude 4.5 Haiku)
  5. Register MCP tools (via AgentCore Gateway HTTP/SSE)
  6. Register Python tools (score_orders, reclassify_order)
  7. Create Agent instance with system prompt

## Component 2: Agent Configuration

- **Module**: `config.py`
- **Responsibility**: Load and validate all agent settings from environment
- **Pattern**: Environment-Based Configuration (Pattern 5)
- **Validates at startup**:
  - Scoring weights sum to 1.0 (tolerance +/-0.001)
  - P1 threshold > P2 threshold > 0
  - Bedrock model ID is non-empty
  - MCP Gateway URL is non-empty
- **Fails fast**: If configuration invalid, agent exits with clear error

## Component 3: Scoring Engine

- **Module**: `scoring.py`
- **Responsibility**: Pure Python priority scoring algorithm
- **Pattern**: Scoring as Pure Python (Pattern 3)
- **Functions**:
  - `compute_urgency_score(due_date)` — discrete bracket mapping
  - `compute_tier_score(tier)` — fixed mapping (100/60/25)
  - `compute_value_score(value, min_val, max_val)` — min-max normalization
  - `compute_complexity_score(machine_types)` — fixed mapping (100/60/40)
  - `score_orders(orders, customers, weights, thresholds)` — full pipeline
  - `classify(weighted_score, thresholds)` — P1/P2/P3 assignment
  - `reclassify(orders, override_order_id, new_priority, weights, thresholds)` — pin + re-evaluate
- **Key property**: Deterministic — same input always produces same output
- **Registered as**: Strands Python tool (LLM calls it after fetching MCP data)

## Component 4: Pydantic Schema Models

- **Module**: `models/schemas.py`
- **Responsibility**: Input/output validation for all agent data
- **Pattern**: Input Validation (Pattern 6)
- **Models**: ScoringWeights, PriorityThresholds, CriterionScores, ScoredOrder, PrioritySummary, OrderTableRow, PriorityGroupTable, OrderExplanation, SharedPrioritizedOrders, ReclassifyInput, ClassificationAuditEntry
- **Validates**: order_id format, priority enum, weight sum, threshold ordering

## Component 5: System Prompt

- **Module**: `prompts/system_prompt.py`
- **Responsibility**: Define agent persona, tool usage instructions, failure handling rules
- **Contents**:
  - Agent role: "You are the Impact Assessment Agent for DisruptionAI"
  - Available tools: MCP tools (get_orders, get_customers, update_order_priority, write_audit_entry) + Python tools (score_orders, reclassify_order, get_priority_summary)
  - Workflow: fetch data -> call score_orders -> write shared context -> present summary
  - Failure handling rules (per BR-IA-12, BR-IA-13)
  - Presentation format (summary first, tables on request, explanation on request)

## Component 6: Structured Logger

- **Module**: `logging_config.py`
- **Responsibility**: JSON-formatted logging to stdout
- **Pattern**: Structured Agent Logging (Pattern 4)
- **Fields**: timestamp, level, agent_name, session_id, duration_ms, message
- **Destination**: stdout (captured by AgentCore runtime to CloudWatch)

---

## Tool Registration

The agent registers two categories of tools:

### MCP Tools (via AgentCore Gateway HTTP/SSE)
| Tool | MCP Server | Purpose |
|------|-----------|---------|
| get_orders | ERP Data MCP | Fetch Florida active orders |
| get_customers | ERP Data MCP | Fetch customer tier data |
| update_order_priority | ERP Data MCP | Persist P1/P2/P3 classification |
| write_audit_entry | Audit MCP | Log decisions to audit trail |

### Python Tools (local, registered with Strands)
| Tool | Module | Purpose |
|------|--------|---------|
| score_orders | scoring.py | Run priority scoring algorithm |
| reclassify_order | scoring.py | Handle Planner override + re-evaluate |
| get_priority_summary | scoring.py | Generate distribution summary text |
| explain_classification | scoring.py | Generate per-order explanation text |

---

## Cross-Cutting Concerns

| Concern | Component | Pattern |
|---------|-----------|---------|
| LLM retry | Strands Agent | Exponential backoff (Pattern 1) |
| MCP failure handling | System Prompt | Failure rules (Pattern 2) |
| Scoring performance | Scoring Engine | Pure Python (Pattern 3) |
| Logging | Structured Logger | JSON middleware (Pattern 4) |
| Configuration | Agent Configuration | Environment variables (Pattern 5) |
| Input validation | Pydantic Models | Schema enforcement (Pattern 6) |
| Fail-closed | Agent Entry Point | Global wrapper (Pattern 7) |

---

## Data Flow

```
1. Orchestrator invokes agent("Analyze Florida orders")
      |
      v
2. LLM calls get_orders(plant="Florida", status="Active")
      |  (HTTP/SSE to AgentCore Gateway -> ERP Data MCP)
      v
3. LLM calls get_customers()
      |  (HTTP/SSE to AgentCore Gateway -> ERP Data MCP)
      v
4. LLM calls score_orders(orders, customers, weights, thresholds)
      |  (local Python tool -- deterministic, < 1ms)
      v
5. LLM calls update_order_priority for each order
      |  (HTTP/SSE to AgentCore Gateway -> ERP Data MCP)
      v
6. LLM calls write_audit_entry(classification summary)
      |  (HTTP/SSE to AgentCore Gateway -> Audit MCP)
      v
7. Agent writes shared context to AgentCore Memory
      |
      v
8. Agent presents summary to Orchestrator
```
