# Integration Test Instructions — DisruptionAI

## Purpose

Test interactions between units to ensure the full disruption response workflow functions end-to-end. Integration tests require live AWS services (DynamoDB, Bedrock, AgentCore).

## Prerequisites

- AWS credentials with access to DynamoDB, Bedrock, and AgentCore
- DynamoDB tables deployed (via `cdk deploy DisruptionAI-Database`)
- Seed data loaded (via `erp-data-mcp-seed` CLI)
- AgentCore agents registered and running
- MCP servers accessible via AgentCore Gateway

## Integration Test Scenarios

### Scenario 1: ERP Data MCP to DynamoDB

**Tests**: MCP tools read/write against live DynamoDB tables.

**Setup**:
```bash
# Deploy database stack
cd infrastructure && npx cdk deploy DisruptionAI-Database --require-approval never
cd ..

# Seed test data
source /tmp/disruptionai-venv/bin/activate
erp-data-mcp-seed
```

**Test Steps**:
1. Start ERP Data MCP server: `python -m erp_data_mcp.server`
2. Use MCP client to call `get_orders_by_plant` with plant="Florida"
3. Verify response contains seeded Florida orders
4. Call `update_order_status` to change an order status
5. Call `get_orders_by_plant` again and verify status changed
6. Call `get_capacity_by_plant` with plant="Ohio" and verify capacity data

**Expected Results**:
- All MCP tools return valid JSON matching Pydantic schemas
- DynamoDB reads return seeded data
- DynamoDB writes persist and are readable

### Scenario 2: Audit MCP to DynamoDB

**Tests**: Audit trail write and query against live audit table.

**Test Steps**:
1. Start Audit MCP server: `python -m audit_mcp.server`
2. Call `write_audit_entry` with a test session_id, agent, action, and detail
3. Call `get_session_audit_trail` with the same session_id
4. Verify the written entry appears in the trail
5. Call `get_agent_actions` with session_id and agent filter
6. Verify filtered results match

**Expected Results**:
- Audit entries persist to DynamoDB audit table
- Query by session_id returns correct entries
- GSI query (session-agent-index) filters correctly

### Scenario 3: Impact Assessment Agent with MCP Tools

**Tests**: Agent invokes ERP Data MCP tools via AgentCore Gateway and produces priority classifications.

**Setup**:
```bash
# Ensure ERP Data MCP is registered on AgentCore Gateway
# Set environment variables:
export MCP_GATEWAY_URL="<agentcore-gateway-url>"
export BEDROCK_MODEL_ID="us.anthropic.claude-4-5-haiku-20250514-v1:0"
```

**Test Steps**:
1. Invoke Impact Assessment Agent with: "Assess impact of Florida plant shutdown"
2. Verify agent calls `get_orders_by_plant` tool for Florida
3. Verify agent calls `get_customer_details` for affected customers
4. Verify output contains priority classifications (Critical/High/Medium/Low)
5. Verify scoring follows business rules (revenue weight 0.35, deadline 0.25, customer tier 0.25, complexity 0.15)

**Expected Results**:
- Agent produces structured priority list
- All Florida orders classified with scores
- Critical orders (score >= 80) identified correctly

### Scenario 4: Capacity Optimization Agent with MCP Tools

**Tests**: Agent queries Ohio plant capacity and generates transfer recommendations.

**Test Steps**:
1. Invoke Capacity Optimization Agent with Florida disruption context
2. Verify agent calls `get_capacity_by_plant` for Ohio
3. Verify agent calls `get_manpower_by_plant` for Ohio
4. Verify agent calls `get_materials_inventory` for Ohio
5. Verify output contains available capacity windows and optimization suggestions

**Expected Results**:
- Agent identifies available machine capacity at Ohio
- Manpower and material constraints factored in
- Capacity windows returned with time ranges and utilization percentages

### Scenario 5: Constraint Matching Agent 4-Layer Funnel

**Tests**: Agent runs full constraint funnel against prioritized orders and Ohio capacity.

**Test Steps**:
1. Provide prioritized order list (from Scenario 3) and capacity data (from Scenario 4)
2. Invoke Constraint Matching Agent
3. Verify Layer 1 (Hard Constraints): machine compatibility filtering
4. Verify Layer 2 (Capacity): available capacity window matching
5. Verify Layer 3 (Material): material availability check
6. Verify Layer 4 (Optimization): schedule optimization
7. Verify output contains transfer-eligible and blocked orders with reasons

**Expected Results**:
- Orders flow through 4 funnel layers
- Each layer reduces eligible orders with documented reasons
- Final output: transferable orders with assigned capacity windows

### Scenario 6: Orchestrator End-to-End Workflow

**Tests**: Full 2-round disruption response workflow through Orchestrator.

**Setup**:
```bash
export IMPACT_ASSESSMENT_AGENT_ID="<agent-id>"
export CAPACITY_OPTIMIZATION_AGENT_ID="<agent-id>"
export CONSTRAINT_MATCHING_AGENT_ID="<agent-id>"
export AUDIT_MCP_URL="<agentcore-gateway-url>/audit-mcp"
```

**Test Steps**:
1. Send disruption event: "Florida plant shutdown due to hurricane, 2-week duration"
2. Verify Round 1 executes: Impact Assessment -> Capacity Optimization -> Constraint Matching
3. Verify Orchestrator presents transfer plan to user
4. Send approval: "Approve transfer of critical orders, hold medium priority"
5. Verify Round 2 executes: order status updates via ERP Data MCP
6. Verify audit trail written for all actions
7. Verify session tracker updated with workflow completion

**Expected Results**:
- Full workflow completes in 2 rounds
- Sub-agents invoked in correct sequence
- Audit trail contains entries for each agent action
- Order statuses updated in DynamoDB
- Session tracker shows completed status

### Scenario 7: Frontend to WebSocket to Orchestrator

**Tests**: Frontend connects via WebSocket and receives streaming responses.

**Setup**:
- Deploy WebSocket API stack: `npx cdk deploy DisruptionAI-WebSocket`
- Deploy Frontend stack: `npx cdk deploy DisruptionAI-Frontend`
- Upload frontend build: `aws s3 sync frontend-spa/dist/ s3://<bucket-name>`

**Test Steps**:
1. Open frontend URL in browser
2. Verify WebSocket connection established (green indicator)
3. Type disruption event description and submit
4. Verify streaming tokens appear in chat panel
5. Verify agent badges show which sub-agent is active
6. Verify capacity tracker panel updates with data
7. Submit approval decision
8. Verify Round 2 completes and final summary displayed

**Expected Results**:
- WebSocket connects and maintains connection
- Streaming tokens render in real-time
- Agent transitions visible in UI
- Capacity tracker reflects live data
- Full workflow completable through UI

## Cleanup

```bash
# Remove test data from DynamoDB (optional)
aws dynamodb delete-item --table-name disruptionai-tracker --key '{"session_id":{"S":"test-session"}}'

# Or destroy all stacks
cd infrastructure && npx cdk destroy --all
```
