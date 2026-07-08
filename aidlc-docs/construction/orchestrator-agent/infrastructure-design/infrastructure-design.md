# Infrastructure Design — Unit 7: Orchestrator Agent

## Infrastructure Overview

The Orchestrator Agent is hosted on Bedrock AgentCore managed runtime. It owns no data stores. It invokes three sub-agents via AgentCore API and accesses Audit MCP directly via AgentCore Gateway. Infrastructure footprint is minimal but includes cross-agent invocation permissions.

**AWS Services Used**:
- Bedrock AgentCore (agent hosting and lifecycle)
- Bedrock (Claude 4.5 Haiku model inference)
- AgentCore Gateway (MCP tool routing to Audit MCP)
- AgentCore Memory (session state and shared context coordination)
- CloudWatch Logs (1 log group, captured via AgentCore runtime)
- IAM (1 role for Bedrock + AgentCore invoke + Memory + CloudWatch)

---

## Bedrock AgentCore Configuration

### Agent Registration

| Setting | Value |
|---------|-------|
| Agent Name | `orchestrator-agent` |
| Runtime | Python 3.11+ |
| Framework | Strands Agents SDK |
| Model | Claude 4.5 Haiku (configurable via env) |
| Entry Point | `orchestrator_agent.agent` |

### AgentCore Gateway — MCP Tool Bindings

| MCP Server | Tools Exposed | Gateway Route |
|------------|--------------|---------------|
| Audit MCP | write_audit_entry, get_audit_trail | `/mcp/audit` |

Note: ERP Data MCP is NOT directly bound to the Orchestrator. All ERP data access is delegated to sub-agents.

---

## IAM Role: Orchestrator Agent

**Role Name**: `disruptionai-orchestrator-agent-role`

**Principle**: Least-privilege (SECURITY-06). Orchestrator needs Bedrock model invocation, AgentCore sub-agent invocation, AgentCore Memory read/write, and CloudWatch access.

### Bedrock Model Access

```json
{
  "Effect": "Allow",
  "Action": [
    "bedrock:InvokeModel",
    "bedrock:InvokeModelWithResponseStream"
  ],
  "Resource": [
    "arn:aws:bedrock:*:*:inference-profile/us.anthropic.claude-4-5-haiku-*"
  ]
}
```

### AgentCore Sub-Agent Invocation

```json
{
  "Effect": "Allow",
  "Action": [
    "bedrock:InvokeAgent"
  ],
  "Resource": [
    "arn:aws:bedrock:*:*:agent/impact-assessment-agent",
    "arn:aws:bedrock:*:*:agent/capacity-optimization-agent",
    "arn:aws:bedrock:*:*:agent/constraint-matching-agent"
  ]
}
```

### AgentCore Memory Access

```json
{
  "Effect": "Allow",
  "Action": [
    "bedrock:GetAgentMemory",
    "bedrock:UpdateAgentMemory"
  ],
  "Resource": [
    "arn:aws:bedrock:*:*:agent/orchestrator-agent"
  ]
}
```

### CloudWatch Logs

```json
{
  "Effect": "Allow",
  "Action": [
    "logs:CreateLogStream",
    "logs:PutLogEvents"
  ],
  "Resource": [
    "arn:aws:logs:*:*:log-group:/disruptionai/orchestrator-agent:*"
  ]
}
```

---

## CloudWatch Logs

| Setting | Value |
|---------|-------|
| Log Group Name | `/disruptionai/orchestrator-agent` |
| Retention | 90 days (SECURITY-14) |
| Encryption | AWS-managed key |

Agent writes to stdout. AgentCore runtime routes stdout to CloudWatch.

---

## Data Stores

**None owned.** The Orchestrator Agent does not own any data stores.

| Data | Service | Access Pattern |
|------|---------|----------------|
| Audit trail | Audit MCP (via Gateway) | Write (write_audit_entry) + Read (get_audit_trail) |
| Session state | AgentCore Memory | Read/Write (workflow_session key) |
| Shared context | AgentCore Memory | Read (prioritized_orders, capacity_snapshot — written by sub-agents) |

---

## Security Compliance

| SECURITY Rule | Status | Implementation |
|---------------|--------|----------------|
| SECURITY-01 | N/A | No data stores owned |
| SECURITY-02 | N/A | No network intermediaries (AgentCore managed) |
| SECURITY-03 | Compliant | Structured JSON logging to CloudWatch, 90-day retention |
| SECURITY-05 | Compliant | Pydantic input validation on Planner messages (max 4000 chars) |
| SECURITY-06 | Compliant | Least-privilege IAM: Bedrock invoke + sub-agent invoke + Memory + CloudWatch only |
| SECURITY-07 | N/A | No network config (AgentCore managed) |
| SECURITY-09 | Compliant | No default credentials, error sanitization |
| SECURITY-12 | Compliant | No hardcoded credentials, IAM role via AgentCore |
| SECURITY-14 | Compliant | CloudWatch 90-day retention, agent role cannot delete logs |
| SECURITY-15 | Compliant | Fail-closed wrapper on agent entry point |

---

## CDK Implementation Notes (for Unit 9)

1. **AgentCore agent registration** for orchestrator-agent
2. **AgentCore Gateway MCP tool bindings** (Audit MCP route only)
3. **IAM role** with Bedrock invoke + sub-agent invoke + Memory + CloudWatch permissions
4. **CloudWatch log group** with 90-day retention
5. **Environment variables** injected via AgentCore agent configuration
6. **Cross-agent dependency**: Orchestrator agent depends on Units 4, 5, 6 agent registrations
