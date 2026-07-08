# Infrastructure Design — Unit 4: Impact Assessment Agent

## Infrastructure Overview

The Impact Assessment Agent is hosted on Bedrock AgentCore managed runtime. It owns no data stores — all data access is through MCP tools on AgentCore Gateway. Infrastructure footprint is minimal.

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
| Agent Name | `impact-assessment-agent` |
| Runtime | Python 3.11+ |
| Framework | Strands Agents SDK |
| Model | Claude 4.5 Haiku (configurable via env) |
| Entry Point | `impact_assessment_agent.agent` |

### AgentCore Gateway — MCP Tool Bindings

| MCP Server | Tools Exposed | Gateway Route |
|------------|--------------|---------------|
| ERP Data MCP | get_orders, get_customers, update_order_priority | `/mcp/erp-data` |
| Audit MCP | write_audit_entry | `/mcp/audit` |

MCP servers are registered on AgentCore Gateway as FastMCP services. The agent accesses them via HTTP/SSE — AgentCore handles routing and authorization.

---

## IAM Role: Impact Assessment Agent

**Role Name**: `disruptionai-impact-assessment-agent-role`

**Principle**: Least-privilege (SECURITY-06). Agent only needs Bedrock model invocation and AgentCore/CloudWatch access. No direct DynamoDB access.

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
    "arn:aws:bedrock:*:*:agent/impact-assessment-agent"
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
    "arn:aws:logs:*:*:log-group:/disruptionai/impact-assessment-agent:*"
  ]
}
```

---

## CloudWatch Logs

### Log Group

| Setting | Value |
|---------|-------|
| Log Group Name | `/disruptionai/impact-assessment-agent` |
| Retention | 90 days (SECURITY-14) |
| Encryption | AWS-managed key |

Agent writes to stdout. AgentCore runtime routes stdout to CloudWatch.

---

## Data Stores

**None owned.** The Impact Assessment Agent does not own any data stores. All data access is through MCP tools:

| Data | MCP Server | Access Pattern |
|------|-----------|----------------|
| Production orders | ERP Data MCP | Read (get_orders) + Write (update_order_priority) |
| Customer data | ERP Data MCP | Read (get_customers) |
| Audit trail | Audit MCP | Write (write_audit_entry) |
| Shared context | AgentCore Memory | Write (prioritized_orders key) |

---

## Security Compliance

| SECURITY Rule | Status | Implementation |
|---------------|--------|----------------|
| SECURITY-01 | N/A | No data stores owned |
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

1. **AgentCore agent registration** for impact-assessment-agent
2. **AgentCore Gateway MCP tool bindings** (ERP Data MCP + Audit MCP routes)
3. **IAM role** with Bedrock invoke + AgentCore + CloudWatch permissions
4. **CloudWatch log group** with 90-day retention
5. **Environment variables** injected via AgentCore agent configuration
