# Infrastructure Design — Unit 6: Constraint Matching Agent

## Infrastructure Overview

The Constraint Matching Agent is hosted on Bedrock AgentCore managed runtime. It owns no data stores — all data access is through MCP tools on AgentCore Gateway. Infrastructure footprint is minimal (identical model to Units 4 and 5).

**AWS Services Used**:
- Bedrock AgentCore (agent hosting and lifecycle)
- Bedrock (Claude 4.5 Haiku model inference)
- AgentCore Gateway (MCP tool routing to ERP Data MCP and Audit MCP)
- CloudWatch Logs (1 log group, captured via AgentCore runtime)
- IAM (1 role for Bedrock + AgentCore + CloudWatch access)

---

## Bedrock AgentCore Configuration

### Agent Registration

| Setting | Value |
|---------|-------|
| Agent Name | `constraint-matching-agent` |
| Runtime | Python 3.11+ |
| Framework | Strands Agents SDK |
| Model | Claude 4.5 Haiku (configurable via env) |
| Entry Point | `constraint_matching_agent.agent` |

### AgentCore Gateway — MCP Tool Bindings

| MCP Server | Tools Exposed | Gateway Route |
|------------|--------------|---------------|
| ERP Data MCP | get_machine_capacity, get_materials, get_orders, get_manpower, get_running_tracker, update_running_tracker | `/mcp/erp-data` |
| Audit MCP | write_audit_entry | `/mcp/audit` |

MCP servers are registered on AgentCore Gateway as FastMCP services. The agent accesses them via HTTP/SSE — AgentCore handles routing and authorization.

Note: Unit 6 uses two additional ERP Data MCP tools compared to Units 4/5: `get_running_tracker` and `update_running_tracker` for session-scoped capacity tracker persistence in DynamoDB.

---

## IAM Role: Constraint Matching Agent

**Role Name**: `disruptionai-constraint-matching-agent-role`

**Principle**: Least-privilege (SECURITY-06). Agent only needs Bedrock model invocation and AgentCore/CloudWatch access. No direct DynamoDB access — tracker persistence is through MCP tools.

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

### AgentCore Access

```json
{
  "Effect": "Allow",
  "Action": [
    "bedrock:InvokeAgent",
    "bedrock:GetAgentMemory",
    "bedrock:UpdateAgentMemory"
  ],
  "Resource": [
    "arn:aws:bedrock:*:*:agent/constraint-matching-agent"
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
    "arn:aws:logs:*:*:log-group:/disruptionai/constraint-matching-agent:*"
  ]
}
```

---

## CloudWatch Logs

### Log Group

| Setting | Value |
|---------|-------|
| Log Group Name | `/disruptionai/constraint-matching-agent` |
| Retention | 90 days (SECURITY-14) |
| Encryption | AWS-managed key |

Agent writes to stdout. AgentCore runtime routes stdout to CloudWatch.

---

## Data Stores

**None owned.** The Constraint Matching Agent does not own any data stores. All data access is through MCP tools:

| Data | MCP Server | Access Pattern |
|------|-----------|----------------|
| Machine capacity | ERP Data MCP | Read (get_machine_capacity) |
| Material inventory | ERP Data MCP | Read (get_materials) |
| Production orders | ERP Data MCP | Read (get_orders — Ohio plant) |
| Manpower data | ERP Data MCP | Read (get_manpower) |
| Running tracker | ERP Data MCP | Read/Write (get_running_tracker / update_running_tracker) |
| Audit trail | Audit MCP | Write (write_audit_entry) |
| Shared context (read) | AgentCore Memory | Read (prioritized_orders, capacity_snapshot) |

Note: The running capacity tracker is persisted in DynamoDB via the ERP Data MCP's tracker tools. The agent does not access DynamoDB directly — the MCP server handles all DynamoDB operations. This maintains the least-privilege principle.

---

## Security Compliance

| SECURITY Rule | Status | Implementation |
|---------------|--------|----------------|
| SECURITY-01 | N/A | No data stores owned (tracker in DynamoDB via MCP) |
| SECURITY-02 | N/A | No network intermediaries (AgentCore managed) |
| SECURITY-03 | Compliant | Structured JSON logging to CloudWatch, 90-day retention |
| SECURITY-06 | Compliant | Least-privilege IAM: Bedrock invoke + CloudWatch logs only |
| SECURITY-07 | N/A | No network config (AgentCore managed) |
| SECURITY-09 | Compliant | No default credentials, error sanitization |
| SECURITY-12 | Compliant | No hardcoded credentials, IAM role via AgentCore |
| SECURITY-14 | Compliant | CloudWatch 90-day retention, agent role cannot delete logs |

---

## CDK Implementation Notes (for Unit 9)

These infrastructure resources will be created by the CDK stack (Unit 9):

1. **AgentCore agent registration** for constraint-matching-agent
2. **AgentCore Gateway MCP tool bindings** (ERP Data MCP + Audit MCP routes)
3. **IAM role** with Bedrock invoke + AgentCore + CloudWatch permissions
4. **CloudWatch log group** with 90-day retention
5. **Environment variables** injected via AgentCore agent configuration
