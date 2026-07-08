# Infrastructure Design — Unit 1: ERP Data MCP Server

## Infrastructure Overview

The ERP Data MCP Server requires only data-layer infrastructure. It runs as a Python subprocess (stdio transport) alongside agents on ECS — no standalone compute resources needed.

**AWS Services Used**:
- DynamoDB (6 tables, On-Demand capacity)
- CloudWatch Logs (1 log group, captured via ECS)
- IAM (1 policy for DynamoDB + CloudWatch access)

---

## DynamoDB Tables

### Naming Convention
- Pattern: `disruptionai-{table-name}`
- No environment prefix (MVP single-environment)
- Deletion protection: Disabled (easy teardown for demo)

### Table 1: disruptionai-orders

| Setting | Value |
|---------|-------|
| Partition Key | `order_id` (String) |
| Capacity | On-Demand |
| Encryption | AWS-managed key (SSE default) |
| Point-in-Time Recovery | Disabled (mock data, re-seedable) |

**GSI: plant-status-index**
| Setting | Value |
|---------|-------|
| Partition Key | `plant` (String) |
| Sort Key | `status` (String) |
| Projection | ALL |
| Capacity | On-Demand |

### Table 2: disruptionai-capacity

| Setting | Value |
|---------|-------|
| Partition Key | `machine_type` (String) |
| Sort Key | `plant` (String) |
| Capacity | On-Demand |
| Encryption | AWS-managed key |

### Table 3: disruptionai-manpower

| Setting | Value |
|---------|-------|
| Partition Key | `plant` (String) |
| Capacity | On-Demand |
| Encryption | AWS-managed key |

### Table 4: disruptionai-materials

| Setting | Value |
|---------|-------|
| Partition Key | `material_type` (String) |
| Sort Key | `plant` (String) |
| Capacity | On-Demand |
| Encryption | AWS-managed key |

### Table 5: disruptionai-customers

| Setting | Value |
|---------|-------|
| Partition Key | `customer_id` (String) |
| Capacity | On-Demand |
| Encryption | AWS-managed key |

### Table 6: disruptionai-tracker

| Setting | Value |
|---------|-------|
| Partition Key | `session_id` (String) |
| Capacity | On-Demand |
| Encryption | AWS-managed key |

---

## IAM Policy: ERP Data MCP Server

**Policy Name**: `disruptionai-erp-data-mcp-policy`

**Principle**: Least-privilege (SECURITY-06). Scoped to specific table ARNs and specific actions.

### Read-Only Tables (4 tables)

Tables: disruptionai-capacity, disruptionai-manpower, disruptionai-materials, disruptionai-customers

```json
{
  "Effect": "Allow",
  "Action": [
    "dynamodb:GetItem",
    "dynamodb:Query",
    "dynamodb:Scan"
  ],
  "Resource": [
    "arn:aws:dynamodb:*:*:table/disruptionai-capacity",
    "arn:aws:dynamodb:*:*:table/disruptionai-manpower",
    "arn:aws:dynamodb:*:*:table/disruptionai-materials",
    "arn:aws:dynamodb:*:*:table/disruptionai-customers"
  ]
}
```

### Read-Write Tables (2 tables)

Tables: disruptionai-orders, disruptionai-tracker

```json
{
  "Effect": "Allow",
  "Action": [
    "dynamodb:GetItem",
    "dynamodb:Query",
    "dynamodb:Scan",
    "dynamodb:PutItem",
    "dynamodb:UpdateItem"
  ],
  "Resource": [
    "arn:aws:dynamodb:*:*:table/disruptionai-orders",
    "arn:aws:dynamodb:*:*:table/disruptionai-orders/index/*",
    "arn:aws:dynamodb:*:*:table/disruptionai-tracker"
  ]
}
```

### Seed Data Permission (Conditional)

For seed data loading only (can be a separate policy or inline during setup):

```json
{
  "Effect": "Allow",
  "Action": [
    "dynamodb:PutItem",
    "dynamodb:BatchWriteItem"
  ],
  "Resource": [
    "arn:aws:dynamodb:*:*:table/disruptionai-*"
  ]
}
```

**Note**: Seed data permission uses wildcard on table name suffix for convenience during initial data load. This is acceptable because it's scoped to `disruptionai-*` tables only and used only during setup.

---

## CloudWatch Logs

### Log Group

| Setting | Value |
|---------|-------|
| Log Group Name | `/disruptionai/erp-data-mcp` |
| Retention | 90 days (SECURITY-14) |
| Encryption | AWS-managed key |

**Note**: The MCP server writes to stdout. ECS task definition routes stdout to this CloudWatch log group. No direct CloudWatch SDK calls from the MCP server.

### IAM Permission for Logging

```json
{
  "Effect": "Allow",
  "Action": [
    "logs:CreateLogStream",
    "logs:PutLogEvents"
  ],
  "Resource": [
    "arn:aws:logs:*:*:log-group:/disruptionai/erp-data-mcp:*"
  ]
}
```

**Note**: Log group creation and retention policy are managed by CDK (Unit 9). The ECS task role includes this permission. The MCP server itself does not need direct CloudWatch permissions since ECS handles log routing.

---

## Security Compliance

| SECURITY Rule | Status | Implementation |
|---------------|--------|----------------|
| SECURITY-01 | Compliant | DynamoDB encryption at rest (AWS-managed key), TLS in transit (SDK default) |
| SECURITY-02 | N/A | No network intermediaries (stdio transport) |
| SECURITY-06 | Compliant | Least-privilege IAM: specific actions, specific table ARNs |
| SECURITY-07 | N/A | No network config (subprocess, not network-facing) |
| SECURITY-14 | Compliant | CloudWatch log retention 90 days, log group scoped |

---

## CDK Implementation Notes (for Unit 9)

These infrastructure resources will be created by the CDK stack (Unit 9):

1. **6 DynamoDB tables** with On-Demand capacity, AWS-managed encryption
2. **1 GSI** on orders table (plant-status-index)
3. **1 CloudWatch log group** with 90-day retention
4. **IAM policy statements** attached to ECS task role
5. **Table name outputs** exported as CloudFormation outputs for environment variable injection

The MCP server receives table names via environment variables set in the ECS task definition.
