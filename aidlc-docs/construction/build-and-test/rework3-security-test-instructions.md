# Rework Cycle 3 — Security Test Instructions

## Applicable Security Rules

Based on the Rework Cycle 3 requirements, the following SECURITY rules apply:

| Rule | Area | Verification |
|------|------|-------------|
| SECURITY-03 | Agent logging | Structured logging maintained in modified agents |
| SECURITY-04 | Frontend headers | HTTP security headers on CloudFront |
| SECURITY-05 | Input validation | Tool interface validation on new staging tools |
| SECURITY-09 | Error handling | Fail-closed patterns in data staging |
| SECURITY-10 | Supply chain | New frontend deps (recharts, remark-gfm) pinned |
| SECURITY-11 | Secure design | Data staging isolation |
| SECURITY-15 | Exception handling | Fail-closed on staging errors |

## Test 1: SECURITY-03 — Structured Logging

### Backend Agents
Verify all modified agent files maintain structured logging:

```bash
# Check that all agent files use the logging module (not print statements)
grep -rn "print(" orchestrator-agent/src/orchestrator_agent/agent.py || echo "PASS: No print statements"
grep -rn "print(" impact-assessment-agent/src/impact_assessment_agent/agent.py || echo "PASS: No print statements"
grep -rn "print(" capacity-optimization-agent/src/capacity_optimization_agent/agent.py || echo "PASS: No print statements"
grep -rn "print(" constraint-matching-agent/src/constraint_matching_agent/agent.py || echo "PASS: No print statements"

# Verify logger is configured in each agent
grep -l "logging.getLogger" orchestrator-agent/src/orchestrator_agent/agent.py
grep -l "logging.getLogger" impact-assessment-agent/src/impact_assessment_agent/agent.py
grep -l "logging.getLogger" capacity-optimization-agent/src/capacity_optimization_agent/agent.py
grep -l "logging.getLogger" constraint-matching-agent/src/constraint_matching_agent/agent.py
```

### Expected: All agents use `logging.getLogger`, no `print()` in production code.

## Test 2: SECURITY-04 — HTTP Security Headers

Verify CloudFront response headers:

```bash
curl -sI https://d6o0q6xbaxa8j.cloudfront.net | grep -iE "(strict-transport|x-content-type|x-frame|content-security|referrer-policy)"
```

### Expected Headers
- `Strict-Transport-Security: max-age=31536000; includeSubDomains`
- `X-Content-Type-Options: nosniff`
- `X-Frame-Options: DENY` or `SAMEORIGIN`
- `Content-Security-Policy: default-src 'self' ...`
- `Referrer-Policy: strict-origin-when-cross-origin`

## Test 3: SECURITY-05 — Input Validation on New Tool Interfaces

### Data Staging Tools
Verify `stage_erp_data` tools validate input before staging:

```bash
# Check for input validation in staging tools
grep -A5 "def stage_erp_data" impact-assessment-agent/src/impact_assessment_agent/agent.py
grep -A5 "def stage_erp_data" capacity-optimization-agent/src/capacity_optimization_agent/agent.py
grep -A5 "def stage_erp_data" constraint-matching-agent/src/constraint_matching_agent/agent.py
```

### Expected: Tools validate that input data is present and well-formed before staging.

## Test 4: SECURITY-09 — Fail-Closed Error Handling

### Data Staging Error Paths
Verify staging tools return error messages (not exceptions) on failure:

```bash
# Check for try/except in staging tools
grep -B2 -A10 "stage_erp_data" impact-assessment-agent/src/impact_assessment_agent/agent.py | grep -E "(try|except|error|Error)"
```

### Orchestrator Fail-Closed
Verify `run_agent` wrapper catches all exceptions:

```bash
grep -A20 "def run_agent" orchestrator-agent/src/orchestrator_agent/agent.py | grep -E "(except|Exception|error)"
```

### Expected: All error paths return safe error results, never propagate raw exceptions.

## Test 5: SECURITY-10 — Supply Chain (Frontend Dependencies)

### Verify Pinned Versions

```bash
cd frontend-spa
# Check that recharts and remark-gfm are pinned to exact versions
grep '"recharts"' package.json
grep '"remark-gfm"' package.json

# Verify lock file exists and is committed
ls -la package-lock.json 2>/dev/null || ls -la yarn.lock 2>/dev/null
```

### Expected
- `recharts`: `2.15.0` (exact version)
- `remark-gfm`: `4.0.0` (exact version)
- Lock file exists

### Vulnerability Scan

```bash
cd frontend-spa
npm audit --production
```

### Expected: No critical or high vulnerabilities in production dependencies.

## Test 6: SECURITY-11 — Data Staging Isolation

Verify staged data is isolated per-invocation and not shared across requests:

```bash
# Check that staging uses module-level dict (cleared per invocation)
grep -B5 -A15 "_staged_data" impact-assessment-agent/src/impact_assessment_agent/agent.py | head -30
```

### Expected: Staged data is scoped to the current invocation context, not persisted across requests.

## Test 7: SECURITY-15 — Exception Handling

### Global Error Handlers
Verify all agentcore_server.py files have error handling in the invoke entrypoint:

```bash
for agent in orchestrator-agent impact-assessment-agent capacity-optimization-agent constraint-matching-agent; do
  echo "=== $agent ==="
  grep -c "except" $agent/src/*/agentcore_server.py
done
```

### WebSocket Lambda Error Handling
Verify the Lambda handler catches exceptions and returns safe error messages:

```bash
grep -c "except" infrastructure/lib/websocket-stack.ts
```

### Expected: All entry points have try/except blocks with safe error responses.

## Security Compliance Summary

| Rule | Status | Notes |
|------|--------|-------|
| SECURITY-01 | N/A | No new data stores |
| SECURITY-02 | N/A | No new network intermediaries |
| SECURITY-03 | VERIFY | Check structured logging in modified agents |
| SECURITY-04 | VERIFY | Check CloudFront response headers |
| SECURITY-05 | VERIFY | Check staging tool input validation |
| SECURITY-06 | N/A | No IAM changes in Rework 3 |
| SECURITY-07 | N/A | No network config changes |
| SECURITY-08 | N/A | No auth changes |
| SECURITY-09 | VERIFY | Check fail-closed patterns |
| SECURITY-10 | VERIFY | Check pinned deps + npm audit |
| SECURITY-11 | VERIFY | Check data staging isolation |
| SECURITY-12 | N/A | No auth mechanism changes |
| SECURITY-13 | N/A | No deserialization changes |
| SECURITY-14 | N/A | No alerting changes |
| SECURITY-15 | VERIFY | Check exception handling |
