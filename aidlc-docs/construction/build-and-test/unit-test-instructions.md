# Unit Test Execution — DisruptionAI

## Overview

All unit tests use mocked AWS services (moto for Python, CDK assertions for TypeScript). No live AWS credentials required for unit tests.

## Run All Unit Tests

### Quick Command (all Python units)

```bash
source /tmp/disruptionai-venv/bin/activate

# MCP Servers
cd erp-data-mcp && python -m pytest tests/ -v && cd ..
cd audit-mcp && python -m pytest tests/ -v && cd ..

# Agents
cd impact-assessment-agent && python -m pytest tests/ -v && cd ..
cd capacity-optimization-agent && python -m pytest tests/ -v && cd ..
cd constraint-matching-agent && python -m pytest tests/ -v && cd ..
cd orchestrator-agent && python -m pytest tests/ -v && cd ..
```

### Frontend Tests

```bash
cd frontend-spa
npm test
cd ..
```

### Infrastructure Tests

```bash
cd infrastructure
npm test
cd ..
```

## Expected Results Per Unit

| Unit | Directory | Test Command | Expected Tests | Framework |
|------|-----------|-------------|----------------|-----------|
| Unit 1: ERP Data MCP | `erp-data-mcp/` | `python -m pytest tests/ -v` | 65 pass | pytest + moto |
| Unit 3: Audit MCP | `audit-mcp/` | `python -m pytest tests/ -v` | 28 pass | pytest + moto |
| Unit 4: Impact Assessment | `impact-assessment-agent/` | `python -m pytest tests/ -v` | 57 pass | pytest |
| Unit 5: Capacity Optimization | `capacity-optimization-agent/` | `python -m pytest tests/ -v` | 98 pass | pytest |
| Unit 6: Constraint Matching | `constraint-matching-agent/` | `python -m pytest tests/ -v` | 137 pass | pytest |
| Unit 7: Orchestrator | `orchestrator-agent/` | `python -m pytest tests/ -v` | 60 pass | pytest |
| Unit 8: Frontend | `frontend-spa/` | `npm test` | 24 pass | vitest + testing-library |
| Unit 9: Infrastructure | `infrastructure/` | `npm test` | 34 pass | jest + CDK assertions |

**Total**: 503 tests across 8 units (Unit 2 Weather MCP skipped for MVP)

## Review Test Results

### Python Units
- All tests should show green `PASSED` status
- No warnings about unclosed resources or deprecations
- Coverage reports (if configured): check `htmlcov/` directory

### Frontend
- Vitest outputs pass/fail summary
- Component rendering, state management, and WebSocket tests

### Infrastructure
- Jest outputs pass/fail with CDK assertion details
- Tests validate CloudFormation resource properties (table schemas, IAM policies, security headers)

## Fix Failing Tests

If any tests fail:

1. Read the test output to identify the failing assertion
2. Check if the failure is in test code or application code
3. For moto-related failures: ensure `@mock_aws` decorator is present and tables are created in setup
4. For CDK assertion failures: run `npx cdk synth` to inspect generated CloudFormation
5. For frontend failures: check component props and mock data match expected shapes
6. Rerun the specific test file: `python -m pytest tests/test_specific.py -v`
