# Functional Design Plan — Unit 5: Capacity & Optimization Agent

## Context
- **Unit**: Unit 5 — Capacity & Optimization Agent
- **Primary Stories**: US-04, US-05, US-06
- **Framework**: Strands Agents SDK (Python)
- **MCP Dependencies**: ERP Data MCP (capacity, manpower, materials, orders), Audit MCP

## Execution Steps

- [x] Step 1: Define domain entities (capacity models, delay candidates, constraint models)
- [x] Step 2: Define business logic model (capacity analysis algorithm, delay logic, constraint handling)
- [x] Step 3: Define business rules (thresholds, eligibility criteria, recalculation rules)

## Clarifying Questions

### Question 1: Capacity Window Duration
The stories reference a "10-day rerouting window" for surplus capacity. Should this be:

A) Fixed at 10 business days (2 weeks) — hardcoded
B) Configurable via environment variable (default 10 days)
C) Other (please describe after [Answer]: tag below)

[Answer]: B

### Question 2: Utilization Calculation Method
For machine utilization surplus, how should available hours be calculated across shift types?

A) Additive — sum normal surplus + overtime available + weekend available for total surplus hours
B) Tiered — report each shift type separately, escalate to overtime/weekend only when normal is exhausted
C) Other (please describe after [Answer]: tag below)

[Answer]: B

### Question 3: Bottleneck Identification Logic
US-04 says "identify the primary bottleneck." When comparing Rolling Mill vs Finishing Line:

A) Bottleneck = machine with the LEAST surplus hours (absolute hours)
B) Bottleneck = machine with the LOWEST surplus-to-demand ratio (percentage-based)
C) Other (please describe after [Answer]: tag below)

[Answer]: B

### Question 4: Delay Candidate Eligibility
US-06 says "P3 priority and deadline > 6 weeks." Should the 6-week threshold be:

A) Fixed at 6 weeks (42 days) — hardcoded
B) Configurable via environment variable (default 42 days)
C) Other (please describe after [Answer]: tag below)

[Answer]: B

### Question 5: Freed Capacity Granularity
When calculating capacity freed by delaying an Ohio order, what dimensions should be reported?

A) All 4 dimensions: Rolling Mill hours, Finishing Line hours, material tons, operator hours
B) Only machine hours (Rolling Mill + Finishing Line) — material and manpower are secondary
C) Other (please describe after [Answer]: tag below)

[Answer]: 4

### Question 6: Constraint Application Scope
US-05 says planners can add constraints like "No weekend shifts." When a constraint is applied:

A) It applies globally to the entire capacity snapshot (all machines, all calculations)
B) It can be scoped per machine type (e.g., "No weekend shifts on Rolling Mill only")
C) Other (please describe after [Answer]: tag below)

[Answer]: A

### Question 7: Post-Delay Recalculation Trigger
After the planner approves/rejects all delay candidates, when does recalculation happen?

A) After EACH individual delay decision (immediate recalculation per decision)
B) After ALL delay decisions are made (batch recalculation at the end)
C) Other (please describe after [Answer]: tag below)

[Answer]: A
