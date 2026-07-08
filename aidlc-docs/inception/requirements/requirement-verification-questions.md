# Requirements Verification Questions — DisruptionAI

Please answer the following questions to help clarify the requirements for the Agentic AI-Powered Dynamic Production Scheduling system. Fill in the letter choice after each `[Answer]:` tag.

---

## Question 1: Target Runtime Environment
What is the target deployment environment for this application?

A) AWS Cloud (serverless — Lambda, API Gateway, DynamoDB)
B) AWS Cloud (containerized — ECS/Fargate, RDS)
C) Local development only (hackathon demo — runs on developer machine)
D) Other (please describe after [Answer]: tag below)

[Answer]: ECS/Fargate, and DynamoDB for database

---

## Question 2: Programming Language
What is the primary programming language for the backend/agent logic?

A) Python
B) TypeScript/Node.js
C) Java
D) Other (please describe after [Answer]: tag below)

[Answer]: Python

---

## Question 3: AI/LLM Provider for the Agent
Which AI/LLM provider should power the agentic reasoning?

A) Amazon Bedrock (Claude via Bedrock Agents)
B) Amazon Bedrock (Claude via Strands Agents SDK)
C) OpenAI (GPT-4)
D) Direct Anthropic API (Claude)
E) Other (please describe after [Answer]: tag below)

[Answer]: Claude via Strands Agents SDK

---

## Question 4: Frontend / Chat UI Framework
What technology should be used for the conversational UI (Work Package 9)?

A) React (Next.js or Vite-based SPA)
B) Streamlit (Python-based rapid prototyping)
C) Chainlit (Python-based chat UI for LLM apps)
D) Plain HTML/CSS/JS (minimal frontend)
E) Other (please describe after [Answer]: tag below)

[Answer]: React

---

## Question 5: Data Storage for Mock Data Layer
How should the mock ERP data (Work Package 1) be stored?

A) In-memory data structures (Python dicts/lists or JS objects) — simplest for hackathon
B) SQLite database — lightweight relational DB, file-based
C) DynamoDB (AWS) — cloud NoSQL
D) JSON files on disk — flat file storage
E) Other (please describe after [Answer]: tag below)

[Answer]: DynamoDB

---

## Question 6: Agent Tool Implementation Pattern
How should the agent's tools (query orders, check capacity, run constraint matching, etc.) be implemented?

A) As Python/JS functions registered as tools with the agent framework (function-calling pattern)
B) As REST API endpoints that the agent calls
C) As AWS Lambda functions invoked by Bedrock Agents action groups
D) Other (please describe after [Answer]: tag below)

[Answer]: A

---

## Question 7: Scope for Hackathon Demo
What is the priority scope for the initial build?

A) Full end-to-end (Phase 0 through Phase 4 with all work packages) — complete demo
B) Core workflow only (Phase 0 through Phase 3 Step 4) — skip Phase 4 execution
C) Minimum viable demo (Phase 0, Phase 1, Phase 2, and Phase 3 Step 3 only) — focus on the core constraint matching engine
D) Other (please describe after [Answer]: tag below)

[Answer]: C

---

## Question 8: Authentication and Multi-User Support
Does the application need authentication or multi-user support?

A) No — single-user demo, no authentication needed
B) Basic authentication (username/password) for demo purposes
C) AWS Cognito or similar identity provider
D) Other (please describe after [Answer]: tag below)

[Answer]: Cognito

---

## Question 9: Real-Time vs Request-Response Agent Interaction
How should the agent communicate with the frontend during long reasoning chains?

A) Streaming responses (tokens appear as the agent thinks — like ChatGPT)
B) Request-response (user sends message, waits for complete response)
C) WebSocket-based bidirectional communication
D) Other (please describe after [Answer]: tag below)

[Answer]: Streaming responses

---

## Question 10: Inline Approval Mechanism
How should the Planner approve/reject agent recommendations in the chat UI?

A) Inline buttons embedded in chat messages (Approve / Reject / Skip)
B) Text-based commands (Planner types "approve", "reject", "skip")
C) Side panel with structured approval form
D) Other (please describe after [Answer]: tag below)

[Answer]: C

---

## Question 11: Audit Trail Storage
Where should the decision audit trail (every human and AI decision with timestamp) be stored?

A) In-memory log displayed in the UI — sufficient for demo
B) Persistent file/database log — survives restarts
C) Both — in-memory for display, persistent for review
D) Other (please describe after [Answer]: tag below)

[Answer]: B

---

## Question 12: What-If Scenario Handling
How sophisticated should the what-if support be?

A) Full what-if: Agent recalculates entire constraint funnel with modified parameters and shows updated recommendations
B) Simplified what-if: Agent provides directional estimates ("adding weekend shifts would free ~40 hours") without full recalculation
C) Other (please describe after [Answer]: tag below)

[Answer]: A

---

## Question 13: Security Extensions
Should security extension rules be enforced for this project?

A) Yes — enforce all SECURITY rules as blocking constraints (recommended for production-grade applications)
B) No — skip all SECURITY rules (suitable for PoCs, prototypes, and experimental projects)
C) Other (please describe after [Answer]: tag below)

[Answer]: A

---

## Question 14: Customer Communication Drafting
How should the agent draft customer communications (Phase 3 Step 4)?

A) AI-generated context-aware emails using the LLM — personalized per customer/order situation
B) Template-based emails with variable substitution — structured but less personalized
C) Both — AI drafts with template structure as guardrails
D) Other (please describe after [Answer]: tag below)

[Answer]: B

---

## Question 15: Demo Data Reset
Should the application support resetting mock data to its initial state for repeated demos?

A) Yes — one-click reset to initial state
B) No — data persists across sessions
C) Other (please describe after [Answer]: tag below)

[Answer]: B

---
