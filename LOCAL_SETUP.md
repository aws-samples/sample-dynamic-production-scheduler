# DisruptionAI — Local Development Setup

Step-by-step guide for a new developer to clone the repo and get running locally.

## Prerequisites

Install these before starting:

| Tool | Version | Install |
|------|---------|---------|
| Git | Latest | `brew install git` or [git-scm.com](https://git-scm.com) |
| Node.js | 22+ | `brew install node` or [nodejs.org](https://nodejs.org) |
| Python | 3.11+ | `brew install python@3.11` or [python.org](https://python.org) |
| AWS CLI v2 | Latest | `brew install awscli` or [AWS docs](https://docs.aws.amazon.com/cli/latest/userguide/getting-started-install.html) |
| pip | Latest | Comes with Python |

## 1. Clone the Repository

```bash
git clone git@ssh.gitlab.aws.dev:automanufacturing-builder-madness-2026-team-5/dynamic-production-scheduler.git
cd dynamic-production-scheduler
```

## 2. Configure AWS Credentials

You need AWS credentials with access to the shared account (us-east-1):

```bash
aws configure
# AWS Access Key ID: <your-key>
# AWS Secret Access Key: <your-secret>
# Default region name: us-east-1
# Default output format: json
```

Verify access:

```bash
aws sts get-caller-identity
```

## 3. Frontend Setup

The frontend is a React + TypeScript + Tailwind SPA using Vite.

```bash
cd frontend-spa
npm install
```

The `.env` and `public/config.json` files are already committed with the shared environment values. You should not need to change them unless the backend has been redeployed to a different account.

Start the dev server:

```bash
npm run dev
```

The app runs at `http://localhost:5173`. It connects to the deployed AWS backend (Lambda Function URL, Cognito, etc.).

To sign in:
1. Open `http://localhost:5173`
2. Click "Sign Up" and register with your email
3. Check your email for the Cognito verification code
4. Enter the code to confirm your account
5. Sign in with your email and password

Run frontend tests:

```bash
npm run test
```

## 4. Python Agent Setup (Optional)

Each agent has its own directory with a `pyproject.toml`. Set up any agent you want to work on:

```bash
# Example: orchestrator agent
cd orchestrator-agent
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
```

Run tests:

```bash
python3 -m pytest tests/ -v
```

Repeat for any agent you need:

```bash
# Available agents:
# orchestrator-agent/
# impact-assessment-agent/
# capacity-optimization-agent/
# constraint-matching-agent/
# erp-data-mcp/
# audit-mcp/
```

## 5. Infrastructure Setup (Optional)

Only needed if you're modifying CDK stacks:

```bash
cd infrastructure
npm install
```

Synthesize (dry-run) to check for errors:

```bash
npx cdk synth
```

Do NOT run `cdk deploy` locally unless you know what you're doing — the CI/CD pipeline handles deployments to the shared account.

## 6. Development Workflow

### Making Changes

1. Create a feature branch:
   ```bash
   git checkout -b feature/my-change
   ```

2. Make your changes, commit, and push:
   ```bash
   git add .
   git commit -m "feat: description of change"
   git push origin feature/my-change
   ```

3. Open a Merge Request in GitLab. The pipeline runs `build:frontend` and `build:mcp-lambdas` to validate your code compiles.

4. Once the MR pipeline passes and you get a review, merge to `main`. This triggers the full deploy pipeline (infra → agents → frontend).

### What Gets Deployed Automatically

When you merge to `main`, the GitLab CI/CD pipeline:
- Builds the frontend and MCP Lambda bundles
- Deploys all 9 CDK stacks (`cdk deploy --all`)
- Deploys all 4 agents via `agentcore deploy`
- Syncs the frontend to S3 and invalidates CloudFront

You do not need to deploy anything manually.

### Branch Naming

Use descriptive branch names:
- `feature/add-transfer-dashboard`
- `fix/cors-headers`
- `refactor/agent-prompts`

## 7. Project Structure Overview

```
dynamic-production-scheduler/
├── frontend-spa/                # React SPA (Vite + TypeScript + Tailwind)
├── orchestrator-agent/          # Main orchestrator (Strands SDK)
├── impact-assessment-agent/     # Disruption impact scoring
├── capacity-optimization-agent/ # Capacity reallocation
├── constraint-matching-agent/   # Order rerouting feasibility
├── erp-data-mcp/                # ERP data MCP server (Lambda)
├── audit-mcp/                   # Audit trail MCP server (Lambda)
├── infrastructure/              # CDK stacks + scripts
│   ├── bin/app.ts               # CDK app entry point
│   ├── lib/                     # 9 stack definitions
│   └── scripts/                 # Utility scripts
├── .gitlab-ci.yml               # CI/CD pipeline
├── .bedrock_agentcore.yaml      # AgentCore config
├── README.md                    # Project overview
├── DEPLOYMENT.md                # Full deployment guide
└── test_*.py                    # E2E test scripts
```

## 8. Useful Commands

| Task | Command |
|------|---------|
| Start frontend dev server | `cd frontend-spa && npm run dev` |
| Run frontend tests | `cd frontend-spa && npm run test` |
| Run agent tests | `cd <agent-dir> && python3 -m pytest tests/ -v` |
| Build frontend | `cd frontend-spa && npm run build` |
| CDK synth (dry run) | `cd infrastructure && npx cdk synth` |
| Check AWS identity | `aws sts get-caller-identity` |

## Troubleshooting

### `npm install` fails in frontend-spa
Make sure you're on Node.js 22+: `node --version`

### Python venv activation fails
On macOS/Linux: `source .venv/bin/activate`
On Windows: `.venv\Scripts\activate`

### "User is not confirmed" on sign-in
Check your email for the Cognito verification code and enter it on the confirmation screen.

### "Incorrect username or password"
Cognito requires: minimum 8 characters, uppercase, lowercase, number, and special character.

### Frontend shows blank page or API errors
Check that `frontend-spa/.env` has the correct `VITE_API_URL`. The current deployed URL is already committed — if the backend was redeployed, ask the team for the new URL.

### Agent tests fail with import errors
Make sure you installed the agent in dev mode: `pip install -e ".[dev]"` inside the activated venv.
