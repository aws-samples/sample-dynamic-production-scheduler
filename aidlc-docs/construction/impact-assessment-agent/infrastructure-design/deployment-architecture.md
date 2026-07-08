# Deployment Architecture — Unit 4: Impact Assessment Agent

## Deployment Model

The Impact Assessment Agent is hosted on Bedrock AgentCore managed runtime. AgentCore handles scaling, health checks, and lifecycle management. The agent does not run as a standalone container or subprocess.

```
+-----------------------------------------------------------+
|  Bedrock AgentCore Managed Runtime                        |
|                                                           |
|  +-----------------------------------------------------+ |
|  | Impact Assessment Agent (Python 3.11)                | |
|  |                                                     | |
|  | - Strands Agents SDK                                | |
|  | - Claude 4.5 Haiku (Bedrock)                        | |
|  | - Python tools (scoring engine)                     | |
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
|  | Key: "prioritized_orders"                            | |
|  +-----------------------------------------------------+ |
+-----------------------------------------------------------+
```

## Communication Paths

| From | To | Protocol | Purpose |
|------|----|----------|---------|
| Orchestrator | Impact Assessment Agent | AgentCore invoke | Start classification |
| Agent | Claude 4.5 Haiku | Bedrock API (HTTPS) | LLM reasoning |
| Agent | ERP Data MCP | HTTP/SSE via Gateway | Order and customer data |
| Agent | Audit MCP | HTTP/SSE via Gateway | Audit trail writes |
| Agent | AgentCore Memory | AgentCore API | Shared context writes |

## Environment Variables

Injected via AgentCore agent configuration at deployment time.

| Variable | Example Value | Purpose |
|----------|--------------|---------|
| BEDROCK_MODEL_ID | us.anthropic.claude-4-5-haiku-20250514-v1:0 | LLM model for agent reasoning |
| MCP_GATEWAY_URL | https://agentcore-gateway.us-east-1.amazonaws.com | AgentCore Gateway endpoint |
| WEIGHT_URGENCY | 0.40 | Scoring weight: urgency criterion |
| WEIGHT_CUSTOMER_TIER | 0.25 | Scoring weight: customer tier criterion |
| WEIGHT_ORDER_VALUE | 0.20 | Scoring weight: order value criterion |
| WEIGHT_MACHINE_COMPLEXITY | 0.15 | Scoring weight: machine complexity criterion |
| P1_THRESHOLD | 75 | Score >= this = P1 (Critical) |
| P2_THRESHOLD | 50 | Score >= this = P2 (High) |
| LOG_LEVEL | INFO | Logging verbosity |

No secrets or credentials in environment variables. Authentication is via IAM role attached to the AgentCore agent runtime.

---

## Packaging and Deployment

### Package Structure

```
impact-assessment-agent/
  src/
    impact_assessment_agent/
      __init__.py
      agent.py
      scoring.py
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
| Request received | Agent processes classification request via Strands SDK |
| MCP tool call | Agent calls Gateway endpoint (HTTP/SSE), Gateway routes to MCP server |
| LLM call | Strands SDK calls Bedrock InvokeModel for Claude 4.5 Haiku |
| Completion | Agent returns result, AgentCore manages process cleanup |
| Error | Fail-closed wrapper catches exceptions, logs error, returns safe error response |
| Idle timeout | AgentCore manages process lifecycle (no long-running process) |

AgentCore handles scaling, health checks, and cold start management. The agent code is stateless — all shared state goes through AgentCore Memory.
