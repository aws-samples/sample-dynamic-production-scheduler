# Unit of Work — Story Map

## Story-to-Unit Mapping

| Story | Description | Primary Unit | Supporting Units |
|-------|------------|-------------|-----------------|
| US-01 | Receive Proactive Disruption Alert | Unit 7: Orchestrator | Unit 2: Weather MCP (optional), Unit 8: Frontend |
| US-02 | View Prioritized Florida Orders | Unit 4: Impact Assessment Agent | Unit 1: ERP Data MCP, Unit 8: Frontend |
| US-03 | Reclassify Order Priority | Unit 4: Impact Assessment Agent | Unit 1: ERP Data MCP, Unit 3: Audit MCP, Unit 7: Orchestrator |
| US-04 | Review Ohio Plant Capacity Snapshot | Unit 5: Capacity & Optimization Agent | Unit 1: ERP Data MCP, Unit 8: Frontend |
| US-05 | Add Planner Constraints to Capacity | Unit 5: Capacity & Optimization Agent | Unit 7: Orchestrator, Unit 8: Frontend |
| US-06 | Review and Approve Ohio Order Delays | Unit 5: Capacity & Optimization Agent | Unit 1: ERP Data MCP, Unit 8: Frontend |
| US-07 | Evaluate Orders Through 4-Layer Funnel | Unit 6: Constraint Matching Agent | Unit 1: ERP Data MCP, Unit 8: Frontend |
| US-08 | Approve, Skip, or Reject Transfers | Unit 6: Constraint Matching Agent | Unit 1: ERP Data MCP, Unit 3: Audit MCP, Unit 7: Orchestrator, Unit 8: Frontend |
| US-09 | Detect and Flag Cascade Impact | Unit 6: Constraint Matching Agent | Unit 1: ERP Data MCP |
| US-10 | View Streaming Agent Responses | Unit 8: Frontend | Unit 7: Orchestrator |

## Unit-to-Story Mapping

| Unit | Primary Stories | Supporting Stories |
|------|----------------|-------------------|
| Unit 1: ERP Data MCP | — | US-02, US-03, US-04, US-06, US-07, US-08, US-09 |
| Unit 2: Weather MCP | — | US-01 (OPTIONAL — MVP uses manual trigger) |
| Unit 3: Audit MCP | — | US-03, US-08 |
| Unit 4: Impact Assessment Agent | US-02, US-03 | — |
| Unit 5: Capacity & Optimization Agent | US-04, US-05, US-06 | — |
| Unit 6: Constraint Matching Agent | US-07, US-08, US-09 | — |
| Unit 7: Orchestrator Agent | US-01, US-05 | US-03, US-08, US-10 |
| Unit 8: Frontend | US-10 | US-01, US-02, US-04, US-05, US-06, US-07, US-08 |
| Unit 9: Infrastructure | — | All stories (foundation) |

## Coverage Verification

All 10 user stories are assigned to at least one primary unit:

- [x] US-01: Orchestrator Agent (primary)
- [x] US-02: Impact Assessment Agent (primary)
- [x] US-03: Impact Assessment Agent (primary)
- [x] US-04: Capacity & Optimization Agent (primary)
- [x] US-05: Capacity & Optimization Agent (primary)
- [x] US-06: Capacity & Optimization Agent (primary)
- [x] US-07: Constraint Matching Agent (primary)
- [x] US-08: Constraint Matching Agent (primary)
- [x] US-09: Constraint Matching Agent (primary)
- [x] US-10: Frontend (primary)

## Story Distribution by Development Phase

### Phase 1 — Data Layer (Units 1-3)
No primary stories. These units provide data access infrastructure for Phase 2 agents.

### Phase 2 — Agent Layer (Units 4-7)
- US-01, US-02, US-03, US-04, US-05, US-06, US-07, US-08, US-09
- 9 of 10 stories have their primary implementation in this phase

### Phase 3 — Presentation Layer (Unit 8)
- US-10 (primary)
- US-01 through US-09 (supporting — UI rendering of agent outputs)

### Phase 4 — Infrastructure (Unit 9)
- No primary stories. Provides deployment foundation for all units.
