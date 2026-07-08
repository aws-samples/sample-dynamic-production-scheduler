# Unit of Work Dependencies — DisruptionAI

## Dependency Matrix

| Unit | Depends On | Dependency Type |
|------|-----------|----------------|
| Unit 1: ERP Data MCP | DynamoDB tables (Unit 9) | Runtime (can mock locally) |
| Unit 2: Weather MCP | None | Independent (OPTIONAL) |
| Unit 3: Audit MCP | DynamoDB audit table (Unit 9) | Runtime (can mock locally) |
| Unit 4: Impact Assessment Agent | Unit 1 (ERP Data MCP), AgentCore Memory | MCP tool calls, SDK |
| Unit 5: Capacity & Optimization Agent | Unit 1 (ERP Data MCP), AgentCore Memory | MCP tool calls, SDK |
| Unit 6: Constraint Matching Agent | Unit 1 (ERP Data MCP), Unit 5 (post-delay capacity), AgentCore Memory | MCP tool calls, SDK |
| Unit 7: Orchestrator Agent | Units 4-6, Unit 3 (Audit MCP), Unit 2 (Weather MCP, optional), AgentCore Memory | Tool calls, MCP |
| Unit 8: Frontend | Unit 7 (Orchestrator via WebSocket) | WebSocket API |
| Unit 9: Infrastructure | None (defines resources for all units) | Independent |

## Development Sequence with Dependencies

```
Phase 1 - Data Layer (no dependencies between these):
  Unit 2: Weather MCP -----> (OPTIONAL, develop if time permits)
  Unit 1: ERP Data MCP ----> (mock DynamoDB locally with moto or local tables)
  Unit 3: Audit MCP -------> (mock DynamoDB locally)

Phase 2 - Agent Layer (depends on Phase 1 MCP servers):
  Unit 4: Impact Assessment Agent --> depends on Unit 1
  Unit 5: Capacity & Optimization Agent --> depends on Unit 1
  Unit 6: Constraint Matching Agent ---> depends on Unit 1, Unit 5
  (Units 4, 5 can be developed in parallel; Unit 6 after Unit 5)
  Unit 7: Orchestrator Agent -----> depends on Units 2, 3, 4, 5, 6

Phase 3 - Presentation Layer:
  Unit 8: Frontend ---------------> depends on Unit 7 (WebSocket API)

Phase 4 - Infrastructure:
  Unit 9: Infrastructure ---------> independent but informed by all units
```

## Critical Path

```
Unit 1 (ERP Data MCP) --> Unit 4/5/6 (Agents) --> Unit 7 (Orchestrator) --> Unit 8 (Frontend)
```

The ERP Data MCP Server is on the critical path because all 3 sub-agents depend on it for data access. Developing it first unblocks the entire agent layer.

## Integration Points

| Integration | Units Involved | Protocol | Notes |
|------------|---------------|----------|-------|
| Agent-to-MCP | Units 4-7 to Units 1-3 | MCP (stdio) | Agents call MCP tools via Strands SDK |
| Agent-to-Agent | Unit 7 to Units 4-6 | Strands SDK tool call | Orchestrator invokes sub-agents |
| Agent-to-Memory | Units 4-7 to AgentCore Memory | AWS SDK | Shared context read/write |
| Backend-to-Frontend | Unit 7 to Unit 8 | WebSocket (WSS) | Streaming tokens + structured data |
| MCP-to-DynamoDB | Units 1, 3 to DynamoDB | AWS SDK (boto3) | CRUD operations |
| Frontend-to-CDN | Unit 8 to CloudFront | HTTPS | Static asset serving |

## Testing Strategy per Phase

| Phase | Testing Approach |
|-------|-----------------|
| Phase 1 (MCP Servers) | Unit tests with mocked DynamoDB (moto). Test each MCP tool independently. |
| Phase 2 (Agents) | Unit tests with mocked MCP servers. Test agent logic and prompt behavior. |
| Phase 3 (Frontend) | Component tests with mocked WebSocket. Test UI rendering and interactions. |
| Phase 4 (Infrastructure) | CDK snapshot tests. Validate resource configurations. |
| Integration | End-to-end with local DynamoDB + all MCP servers + agents + frontend. |
