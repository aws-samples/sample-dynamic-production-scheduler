# Rework Cycle 3 — Build Instructions

## Prerequisites
- Python 3.11 (`/opt/homebrew/bin/python3.11`)
- Node.js 18+ with npm
- AWS CLI v2 configured with account `058264253938` / `us-east-1`
- Access to S3 bucket `bedrock-agentcore-codebuild-sources-058264253938-us-east-1`

## Stream A: Backend Agent Builds

### 1. Validate Python Syntax (All 4 Agents)

```bash
# From workspace root
/opt/homebrew/bin/python3.11 -m py_compile orchestrator-agent/src/orchestrator_agent/agent.py
/opt/homebrew/bin/python3.11 -m py_compile orchestrator-agent/src/orchestrator_agent/agentcore_server.py
/opt/homebrew/bin/python3.11 -m py_compile orchestrator-agent/src/orchestrator_agent/config.py
/opt/homebrew/bin/python3.11 -m py_compile impact-assessment-agent/src/impact_assessment_agent/agent.py
/opt/homebrew/bin/python3.11 -m py_compile impact-assessment-agent/src/impact_assessment_agent/agentcore_server.py
/opt/homebrew/bin/python3.11 -m py_compile capacity-optimization-agent/src/capacity_optimization_agent/agent.py
/opt/homebrew/bin/python3.11 -m py_compile capacity-optimization-agent/src/capacity_optimization_agent/agentcore_server.py
/opt/homebrew/bin/python3.11 -m py_compile constraint-matching-agent/src/constraint_matching_agent/agent.py
/opt/homebrew/bin/python3.11 -m py_compile constraint-matching-agent/src/constraint_matching_agent/agentcore_server.py
```

### 2. Run Unit Tests (All 4 Agents)

```bash
# Orchestrator
cd orchestrator-agent && /opt/homebrew/bin/python3.11 -m pytest tests/ -v && cd ..

# Impact Assessment
cd impact-assessment-agent && /opt/homebrew/bin/python3.11 -m pytest tests/ -v && cd ..

# Capacity Optimization
cd capacity-optimization-agent && /opt/homebrew/bin/python3.11 -m pytest tests/ -v && cd ..

# Constraint Matching
cd constraint-matching-agent && /opt/homebrew/bin/python3.11 -m pytest tests/ -v && cd ..
```

### 3. Redeploy Agents to AgentCore Runtime

```bash
export ACCOUNT_ID=058264253938
/opt/homebrew/bin/python3.11 infrastructure/scripts/redeploy_agents.py
```

Wait for all 4 agents to reach READY status.

## Stream B: Frontend Build

### 1. Install Dependencies

```bash
cd frontend-spa
npm install
```

Verify `recharts@2.15.0` and `remark-gfm@4.0.0` are installed.

### 2. TypeScript Compilation

```bash
npx tsc -b --noEmit
```

### 3. Run Frontend Tests

```bash
npm run test
```

### 4. Production Build

```bash
npm run build
```

Build output goes to `frontend-spa/dist/`.

### 5. Deploy to S3 + CloudFront

```bash
aws s3 sync dist/ s3://disruptionai-frontend-058264253938 --delete
aws cloudfront create-invalidation --distribution-id E3KKSG60PFHFU --paths "/*"
```

## Stream C: WebSocket Lambda

### 1. CDK Deploy (WebSocket Stack)

```bash
cd infrastructure
npx cdk deploy DisruptionAI-WebSocket --require-approval never
```

This redeploys the inline Lambda with the updated `detect_signals` logic.

## Verification

After all streams are deployed:
1. All 4 agents show READY in AgentCore
2. Frontend loads at `https://d6o0q6xbaxa8j.cloudfront.net`
3. WebSocket connects at `wss://x5u9j1d0p7.execute-api.us-east-1.amazonaws.com/prod`
