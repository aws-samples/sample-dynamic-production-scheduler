# Functional Design Plan — Unit 4: Impact Assessment Agent

## Purpose
Design detailed business logic for the Impact Assessment Agent — the agent responsible for evaluating and prioritizing Florida production orders during a disruption event.

## Context
- **Unit**: Unit 4 — Impact Assessment Agent
- **Type**: AI Agent (Strands Agents SDK + Bedrock Claude)
- **Primary Stories**: US-02 (View Prioritized Florida Orders), US-03 (Reclassify Order Priority)
- **Dependencies**: Unit 1 (ERP Data MCP Server) for order and customer data
- **Consumers**: Unit 7 (Orchestrator Agent) invokes this agent; output feeds Unit 5 and Unit 6

## Functional Design Questions

Please answer the following questions to guide the functional design.

### Question 1: Priority Algorithm Weights
What relative weights should the 4 priority criteria have?

A) Equal weights — 25% each for days-to-due-date, customer tier, order value, machine complexity
B) Urgency-heavy — 40% days-to-due-date, 25% customer tier, 20% order value, 15% machine complexity
C) Customer-heavy — 20% days-to-due-date, 40% customer tier, 25% order value, 15% machine complexity
D) Configurable — Store weights in configuration, default to urgency-heavy, allow runtime override
X) Other (please describe after [Answer]: tag below)

[Answer]: D

### Question 2: P1/P2/P3 Threshold Strategy
How should the weighted score map to P1/P2/P3 classifications?

A) Fixed percentile — Top 40% = P1, next 35% = P2, bottom 25% = P3
B) Fixed score thresholds — Score >= 75 = P1, 50-74 = P2, < 50 = P3
C) Dynamic clustering — Use natural breaks in score distribution to determine boundaries
D) Configurable thresholds — Default to fixed score, allow Planner to adjust thresholds
X) Other (please describe after [Answer]: tag below)

[Answer]: D

### Question 3: Reclassification Scope
When the Planner reclassifies an order, should the agent re-run the algorithm?

A) No re-run — Just override the single order's priority, carry forward as-is
B) Re-run affected — If a P2 is moved to P1, re-evaluate other P2s to see if any should shift to P3
C) Full re-run — Re-run entire algorithm with the override as a constraint
X) Other (please describe after [Answer]: tag below)

[Answer]: B

### Question 4: Agent Output Format
How should the agent present prioritized orders to the Planner?

A) Single table — One table with all orders sorted by priority then due date
B) Grouped tables — Separate tables for P1, P2, P3 with subtotals
C) Summary first — Priority distribution summary, then grouped tables on request
X) Other (please describe after [Answer]: tag below)

[Answer]: C

---

## Execution Steps

After questions are answered, the following artifacts will be generated:

- [x] Step 1: Generate `business-logic-model.md` — Priority algorithm, agent tool contracts, scoring model
- [x] Step 2: Generate `business-rules.md` — Classification rules, reclassification rules, validation rules
- [x] Step 3: Generate `domain-entities.md` — Agent state model, shared context schema, input/output contracts

