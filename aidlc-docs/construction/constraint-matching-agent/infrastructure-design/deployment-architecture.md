# Deployment Architecture — Unit 6: Constraint Matching Agent

## Deployment Model

The Constraint Matching Agent is hosted on Bedrock AgentCore managed runtime. AgentCore handles scaling, health checks, and lifecycle management. The agent does not run as a standalone container or subprocess.

```
+-----------------------------------------------------------+
|  Bedrock AgentCore Managed Runtime                        |
|                                                           |
|  +-----------------------------------------------------+ |
|  | Constraint Matching Agent (Python 3.11)              | |
|  |                                                     | |
|  | - Strands Agents SDK                                | |
|  | - Claude 4.5 Haiku (Bedrock)                        | |
|  | - Python tools (funnel engine + tracker)             | |
|  | - Tracker state singleton (in-memory)                | |
|  | - Pydantic validation                               | |
|  | - JSON structured logging                           | |
|  +-----------------------------------------------------+ |
|       |                          |                        |
|       | Bedrock InvokeModel      | HTTP/SSE                |
|       v                          v                        |
|  +--------------+    +-------------------------+          |
|  | Claude 4.5   |    | AgentCore Gateway       |          |
|  | Haiku        |    |                         |          |
|  +--------------+    | +-----+ +-----+         |          |
|                      | | ERP | | Aud |         |          |
|                      | | MCP | | MCP |         |          |
|                      | +-----+ +-----+         |          |
|                      +-------------------------+          |
|       |                                                   |
|       | AgentCore Memory API                              |
|       v                                                   |
|  +-----------------------------------------------------+ |
|  | AgentCore Memory (shared context)                    | |
|  | Reads: prioritized_orders, capacity_snapshot         | |
|  +-----------------------------------------------------+ |
+-----------------------------------------------------------+
```

## Communication Paths

| From | To | Protocol | Purpose |
|------|----|----------|---------|
| Orchestrator | Constraint Matching Agent | AgentCore invoke | Start constraint matching |
| Agent | Claude 4.5 Haiku | Bedrock API (HTTPS) | LLM reasoning and presentation |
| Agent | ERP Data MCP | HTTP/SSE via Gateway | Equipment, material, order, manpower, tracker data |
| Agent | Audit MCP | HTTP/SSE via Gateway | Audit trail writes |
| Agent | AgentCore Memory | AgentCore API | Shared context reads (prioritized_orders, capacity_snapshot) |

## Environment Variables

Injected via AgentCore agent configuration at deployment time.

| Variable | Example Value | Purpose |
|----------|--------------|---------|
| BEDROCK_MODEL_ID | us.anthropic.claude-4-5-haiku-20250514-v1:0 | LLM model for agent reasoning |
| MCP_GATEWAY_URL | https://agentcore-gateway.us-east-1.amazonaws.com | AgentCore Gateway endpoint |
| UTILIZATION_WARNING_PCT | 0.90 | 90% utilization threshold for overtime warning |
| MAX_CASCADE_DEPTH | 5 | Maximum cascade simulation depth |
| CASCADE_TIMEOUT_SECS | 3 | Layer 4 cascade simulation timeout |
| CHECKPOINT_INTERVAL_SECS | 300 | Periodic tracker persistence interval |
| LOG_LEVEL | INFO | Logging verbosity |

No secrets or credentials in environment variables. Authentication is via IAM role attached to the AgentCore agent runtime.

---

## Packaging and Deployment

### Package Structure

```
constraint-matching-agent/
  src/
    constraint_matching_agent/
      __init__.py
      agent.py
      funnel.py
      tracker.py
      config.py
      models/schemas.py
      prompts/system_prompt.py
      logging_config.py
  requirements.txt
```

### Deployment Steps

1. Package agent code as a zip or directory artifact
2. Register agent with AgentCore via CDK (Unit 9)
3. AgentCore installs dependencies from requirements.txt
4. AgentCore starts agent entry point on invocation

### Artifact Size

Minimal — pure Python with 4 pip dependencies. No native extensions, no Docker image required.

---

## Process Lifecycle

| Event | Behavior |
|-------|----------|
| Agent invoked | AgentCore starts Python process, loads agent module |
| Initialization | Agent loads shared context, initializes tracker from DynamoDB or snapshot |
| Priority queue | Agent builds order queue from prioritized_orders (P1 > P2 > P3) |
| Funnel evaluation | Python tool evaluates 4 layers (< 10ms), LLM generates explanation |
| Planner decision | Agent processes approve/reject/skip, updates tracker singleton |
| Tracker persist | Agent calls update_running_tracker MCP tool after each decision |
| Skip/Revisit | Order re-queued or re-evaluated with current tracker state |
| Completion | Agent presents transfer summary, returns control to Orchestrator |
| Error | Fail-closed wrapper catches exceptions, logs error, returns safe response |
| Idle timeout | AgentCore manages process lifecycle |

AgentCore handles scaling, health checks, and cold start management. The agent code is stateless across invocations — all persistent state goes through DynamoDB via MCP tools. Within a single invocation, the tracker singleton enables fast capacity deductions without MCP round-trips for reads.
