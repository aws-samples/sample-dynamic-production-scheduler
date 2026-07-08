# Build Instructions — DisruptionAI

## Prerequisites

- Python 3.11+ (`/opt/homebrew/bin/python3.11` or system python3.11)
- Node.js 18+ with npm
- AWS CDK CLI: `npm install -g aws-cdk`
- AWS credentials configured (for DynamoDB access and CDK deploy)
- Virtual environment recommended for Python units

## Environment Setup

### 1. Create Python Virtual Environment

```bash
python3.11 -m venv /tmp/disruptionai-venv
source /tmp/disruptionai-venv/bin/activate
```

### 2. Install Python Units

Install each Python unit in editable mode with dev dependencies:

```bash
# MCP Servers
pip install -e ./erp-data-mcp
pip install -e ./audit-mcp

# Agents
pip install -e "./impact-assessment-agent[dev]"
pip install -e "./capacity-optimization-agent[dev]"
pip install -e "./constraint-matching-agent[dev]"
pip install -e "./orchestrator-agent[dev]"

# Test dependencies (shared)
pip install pytest pytest-asyncio moto[dynamodb] boto3
```

### 3. Install Frontend Dependencies

```bash
cd frontend-spa
npm install
cd ..
```

### 4. Install Infrastructure Dependencies

```bash
cd infrastructure
npm install
cd ..
```

## Build Steps

### Step 1: Build Python Units

Python units use setuptools and don't require a separate build step beyond installation. Verify imports:

```bash
python -c "from erp_data_mcp.server import mcp; print('erp-data-mcp OK')"
python -c "from audit_mcp.server import mcp; print('audit-mcp OK')"
python -c "from impact_assessment_agent.agent import create_agent; print('impact-assessment OK')"
python -c "from capacity_optimization_agent.agent import create_agent; print('capacity-optimization OK')"
python -c "from constraint_matching_agent.agent import create_agent; print('constraint-matching OK')"
python -c "from orchestrator_agent.agent import create_agent; print('orchestrator OK')"
```

### Step 2: Build Frontend

```bash
cd frontend-spa
npm run build
```

Expected output: `dist/` directory with compiled assets.

### Step 3: Build Infrastructure (TypeScript Compilation)

```bash
cd infrastructure
npx tsc
```

Expected output: No errors. Compiled JS in project root.

### Step 4: Synthesize CDK Templates

```bash
cd infrastructure
npx cdk synth
```

Expected output: CloudFormation templates in `cdk.out/`.

## Build Verification

After all steps complete:
- 6 Python packages importable without errors
- `frontend-spa/dist/` contains `index.html` and JS/CSS assets
- `infrastructure/cdk.out/` contains 5 CloudFormation templates
- No TypeScript compilation errors in frontend or infrastructure

## Troubleshooting

### Python Import Errors
- Ensure virtual environment is activated
- Run `pip install -e ./<unit-name>` again
- Check Python version: `python --version` (must be 3.11+)

### Frontend Build Fails
- Delete `node_modules` and run `npm install` again
- Check Node version: `node --version` (must be 18+)

### CDK Synth Fails
- Ensure `aws-cdk-lib` version matches `package.json` (2.178.0)
- Run `npm install` in `infrastructure/`
- Check AWS credentials: `aws sts get-caller-identity`
