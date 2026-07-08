# Requirements Clarification Questions — DisruptionAI

I detected potential contradictions and ambiguities in your responses that need clarification before proceeding.

---

## Contradiction 1: Scope vs Authentication Complexity
You indicated minimum viable demo scope (Q7: Phase 0, 1, 2, Phase 3 Step 3 only) but also chose AWS Cognito authentication (Q8). Cognito adds significant infrastructure and development effort for a minimum viable demo.

### Clarification Question 1
Given the minimum viable demo scope, how should we handle authentication?

A) Keep Cognito — authentication is a hard requirement even for the MVP demo
B) Defer Cognito to a later iteration — use no authentication for the MVP, add Cognito when expanding scope
C) Use a simplified auth stub — hardcoded demo user with Cognito integration planned for later
D) Other (please describe after [Answer]: tag below)

[Answer]: B

---

## Contradiction 2: Scope vs Customer Communications
You chose minimum viable demo scope (Q7: C — excludes Phase 3 Step 4) but also answered Q14 about customer communication drafting (template-based). Phase 3 Step 4 is the stage that handles customer communications.

### Clarification Question 2
Should customer communications (Phase 3 Step 4) be included in the MVP scope?

A) No — stick with MVP scope (Phase 0, 1, 2, Phase 3 Step 3 only). Q14 answer applies if we expand scope later.
B) Yes — add Phase 3 Step 4 to the MVP scope. The template-based communications are important for the demo.
C) Other (please describe after [Answer]: tag below)

[Answer]: A

---

## Ambiguity 1: React Frontend Specifics
You chose React for the frontend (Q4). React has several common setups.

### Clarification Question 3
Which React setup do you prefer?

A) Vite + React (lightweight SPA, fast dev server, simple deployment)
B) Next.js (SSR/SSG, API routes built-in, more opinionated)
C) Create React App (legacy but familiar)
D) No preference — choose the best fit for a chat-based UI with streaming support
E) Other (please describe after [Answer]: tag below)

[Answer]: A

---

## Ambiguity 2: Streaming with Strands SDK
You chose streaming responses (Q9) with Strands Agents SDK (Q3). Streaming with Strands requires specific backend infrastructure.

### Clarification Question 4
How should the backend expose the streaming agent responses to the React frontend?

A) FastAPI with Server-Sent Events (SSE) — Python backend streams tokens to React via SSE
B) FastAPI with WebSocket — bidirectional streaming connection
C) AWS API Gateway WebSocket API — managed WebSocket with ECS backend
D) No preference — choose the simplest approach that supports streaming with Strands SDK
E) Other (please describe after [Answer]: tag below)

[Answer]: C

---

## Ambiguity 3: Audit Trail Persistence
You chose persistent audit trail (Q11: B) with DynamoDB as the data store (Q5). 

### Clarification Question 5
Should the audit trail be stored in the same DynamoDB instance as the mock ERP data, or separately?

A) Same DynamoDB — single table design or separate table in the same DynamoDB instance
B) Separate storage — audit trail in a different store (e.g., S3, CloudWatch Logs)
C) No preference — choose the simplest approach
D) Other (please describe after [Answer]: tag below)

[Answer]: SEPERATE

---
