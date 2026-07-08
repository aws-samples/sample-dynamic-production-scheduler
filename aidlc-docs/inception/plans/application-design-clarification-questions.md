# Application Design — Clarification Questions

Your answers introduced two technology choices that need clarification before I can design the components accurately.

---

## Clarification 1: AgentCore Memory (Q2)

You chose "Agentcore memory" for shared context. This refers to AWS Bedrock AgentCore's built-in memory capabilities. I need to understand the intended usage:

### Clarification Question 1
How should AgentCore memory be used for shared agent context?

A) Session memory — Use AgentCore's session memory to store shared context (prioritized orders, capacity snapshot) within a single workflow session. Agents read/write to the same session memory.
B) Long-term memory — Use AgentCore's persistent memory store so context survives across sessions and restarts.
C) Session + checkpoint — Use session memory during active workflow, checkpoint key decisions to DynamoDB for audit and recovery.
X) Other (please describe after [Answer]: tag below)

[Answer]: Amazon Bedrock AgentCore Memory is a fully managed service that replaces the need to manually build memory infrastructure (such as manual DynamoDB session table management, vector database indexing, and custom storage logic).

While it replaces the undifferentiated heavy lifting of manual DynamoDB orchestration for agent memory, it is designed as a higher-level abstraction layer that likely utilizes underlying AWS storage technology (including DynamoDB for short-term persistence) under the hood to manage both short-term context and long-term intelligent memory.

### Clarification Question 2
Should AgentCore memory replace DynamoDB for mock ERP data storage as well, or only for inter-agent shared context?

A) Only shared context — AgentCore memory for agent-to-agent state sharing. DynamoDB still stores mock ERP data (orders, capacity, materials).
B) Both — AgentCore memory for everything (shared context + mock data). No DynamoDB.
C) Layered — DynamoDB for persistent mock data, AgentCore memory for transient session state and agent context.
X) Other (please describe after [Answer]: tag below)

[Answer]: only for inter-agent shared context

---

## Clarification 2: MCP Communication Pattern (Q3)

You chose MCP (Model Context Protocol) for agent communication. This is a significant architectural pattern choice. I need to understand the topology:

### Clarification Question 3
How should MCP be structured for the 4-agent system?

A) Each agent as MCP server — Each agent (Production Order, Capacity, Scheduler) runs as a separate MCP server. Orchestrator connects to all three as MCP client.
B) Single MCP server — One MCP server exposes all agent tools. Orchestrator calls tools by name, routing handled internally.
C) Orchestrator as MCP server — Orchestrator exposes the workflow as MCP tools. Sub-agents are internal implementation details, not MCP-exposed.
X) Other (please describe after [Answer]: tag below)

[Answer]: MCP as the interface for the ERP data and other external tools

### Clarification Question 4
For the agent orchestration pattern, you mentioned "tool call, swarm etc." Given the DisruptionAI workflow (Round 1 parallel, Round 2 sequential interactive), which pattern fits best?

A) Tool call — Orchestrator explicitly calls each agent as a tool. Full control over execution order (parallel Round 1, sequential Round 2).
B) Swarm — Agents hand off to each other dynamically. Less centralized control, more autonomous agent behavior.
C) Graph — Define a workflow graph (DAG) where Round 1 nodes run in parallel, Round 2 nodes run sequentially. Orchestrator manages the graph.
X) Other (please describe after [Answer]: tag below)

[Answer]: other - mixed and determine the right architecture based on the agent type

---

Please fill in the [Answer]: tags and let me know when done.
