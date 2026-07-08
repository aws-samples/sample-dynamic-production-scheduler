# NFR Design Plan — Unit 6: Constraint Matching Agent

## Context
- NFR Requirements complete: PERF-CM-01 through 07, REL-CM-01 through 05, OBS-CM-01 through 04, SEC-CM-01 through 05, SCALE-CM-01 through 03
- Tech stack: Same as Units 4/5 (Strands SDK, Claude 4.5 Haiku, AgentCore, FastMCP)
- Patterns from Units 4/5 apply directly; Unit 6 adds funnel-specific patterns

## Plan Steps

- [x] Step 1: Collect user answers to design questions
- [x] Step 2: Generate `nfr-design-patterns.md` with constraint matching patterns
- [x] Step 3: Generate `logical-components.md` with component architecture
- [x] Step 4: Update plan checkboxes, aidlc-state.md, and audit.md

## Questions

The Constraint Matching Agent reuses all established patterns from Units 4/5 (LLM retry, MCP failure handling, structured logging, env config, input validation, fail-closed wrapper). Two Unit 6-specific design questions:

## Question 1
The 4-layer funnel runs as pure Python (like scoring in Unit 4 and capacity calcs in Unit 5). Should the cascade simulation (Layer 4) also be a separate Python tool, or bundled into a single `evaluate_funnel` tool?

A) Single `evaluate_funnel` tool — all 4 layers in one call, simpler LLM orchestration
B) Separate tools per layer — `check_equipment`, `check_material`, `check_utilization`, `simulate_cascade` — more granular LLM control
C) Hybrid — single `evaluate_funnel` for the 4 layers + separate `simulate_cascade` for on-demand re-simulation
X) Other (please describe after [Answer]: tag below)

[Answer]: C

## Question 2
For the running capacity tracker cache (Pattern 8 equivalent from Unit 5), should the tracker be a module-level singleton or passed through function parameters?

A) Module-level singleton — simpler access from all funnel functions, consistent with Unit 5's CapacityState pattern
B) Parameter-based — tracker passed explicitly to each function, more testable and explicit
X) Other (please describe after [Answer]: tag below)

[Answer]: A
