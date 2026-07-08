# Deployment Architecture — Unit 5: Capacity & Optimization Agent

## Deployment Model

The Capacity & Optimization Agent is hosted on Bedrock AgentCore managed runtime. AgentCore handles scaling, health checks, and lifecycle management. The agent does not run as a standalone container or subprocess.

```
+-----------------------------------------------------------+
|  Bedrock AgentCore Managed Runtime                        |
|                                                           |
|  +-----------------------------------------------------+ |
|  | Capacity & Optimization Agent (Python 3.11)          | |
|  |                                                     | |
|  | - Strands Agents SDK                                | |
|  | - Claude 4.5 Haiku (Bedrock)                        | |
|  | - Python tools (capacity engine)                    | |
|  | - Capacity state cache (in-memory)                  | |
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
|  | Key: "capacity_snapshot"                             | |
|  +-----------------------------------------------------+ |
+-----------------------------------------------------------+
```

## Communication Paths

| From | To | Protocol | Purpose |
|------|----|----------|---------|
| Orchestrator | Capacity Optimization Agent | AgentCore invoke | Start capacity analysis |
| Agent | Claude 4.5 Haiku | Bedrock API (HTTPS) | LLM reasoning |
| Agent | ERP Data MCP | HTTP/SSE via Gateway | Capacity, manpower, material, order, customer data |
| Agent | Audit MCP | HTTP/SSE via Gateway | Audit trail writes |
| Agent | AgentCore Memory | AgentCore API | Shared context writes (capacity_snapshot) |

## Environment Variables

Injected via AgentCore agent configuration at deployment time.

| Variable | Example Value | Purpose |
|----------|--------------|---------|
| BEDROCK_MODEL_ID | us.anthropic.claude-4-5-haiku-20250514-v1:0 | LLM model for agent reasoning |
| MCP_GATEWAY_URL | https://agentcore-gateway.us-east-1.amazonaws.com | AgentCore Gateway endpoint |
| REROUTING_WINDOW_DAYS | 10 | Business days for capacity analysis scope |
| DELAY_THRESHOLD_DAYS | 42 | Minimum slack days for delay eligibility |
| UTILIZATION_WARNING_PCT | 0.90 | Utilization threshold for overtime warning |
| LOG_LEVEL | INFO | Logging verbosity |

No secrets or credentials in environment variables. Authentication is via IAM role attached to the AgentCore agent runtime.

---

## Packaging and Deployment

### Package Structure

```
capacity-optimization-agent/
  src/
    capacity_optimization_agent/
      __init__.py
      agent.py
      capacity.py
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
| Request received | Agent processes capacity analysis request via Strands SDK |
| MCP tool call | Agent calls Gateway endpoint (HTTP/SSE), Gateway routes to MCP server |
| LLM call | Strands SDK calls Bedrock InvokeModel for Claude 4.5 Haiku |
| Delay/Constraint | Agent recalculates from in-memory cache (no MCP re-fetch) |
| Completion | Agent returns result, AgentCore manages process cleanup |
| Error | Fail-closed wrapper catches exceptions, logs error, returns safe error response |
| Idle timeout | AgentCore manages process lifecycle (no long-running process) |

AgentCore handles scaling, health checks, and cold start management. The agent code is stateless across invocations — all shared state goes through AgentCore Memory. Within a single invocation, the capacity state cache enables fast recalculations for delay decisions and constraint applications.
