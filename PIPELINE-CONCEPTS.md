# GitLab CI/CD Pipeline - Key Concepts Explained

## Table of Contents
1. [Basic Structure](#basic-structure)
2. [Images and Containers](#images-and-containers)
3. [Stages](#stages)
4. [Jobs](#jobs)
5. [Variables](#variables)
6. [Templates and Anchors](#templates-and-anchors)
7. [Scripts](#scripts)
8. [Tags](#tags)
9. [Dependencies and Needs](#dependencies-and-needs)
10. [Artifacts](#artifacts)
11. [Cache](#cache)
12. [Conditional Execution](#conditional-execution)
13. [Manual Jobs](#manual-jobs)

---

## Basic Structure

```yaml
image: public.ecr.aws/docker/library/node:18-slim
```

**What it does**: Defines the default Docker image for all jobs
**Why it matters**: Every job runs inside a container. This sets the base environment.
**In our pipeline**: We use Node.js 18 as default, but override it for Python jobs

---

## Images and Containers

### Concept
GitLab CI runs each job in an isolated Docker container. Think of it as a fresh, clean computer for each job.

### Example from our pipeline:
```yaml
.python_setup: &python_setup
  image: public.ecr.aws/docker/library/python:3.13-slim
```

**What happens**:
1. GitLab pulls the Python 3.13 image from AWS ECR
2. Creates a container from that image
3. Runs your job inside that container
4. Destroys the container when done

**Why different images**:
- Node.js image: For frontend builds (npm, webpack)
- Python image: For agent bundling, testing, AWS CLI
- Each job gets the right tools for its task

---

## Stages

```yaml
stages:
  - validate
  - test
  - build-and-bundle
  - deploy-infrastructure
  - deploy-agents
  - deploy-frontend
  - verify
```

### Concept
Stages define the execution order of your pipeline. They run sequentially.

### How it works:
```
Stage 1: validate
  ├─ All validate jobs run in parallel
  └─ Wait for ALL to complete
      ↓
Stage 2: test
  ├─ All test jobs run in parallel
  └─ Wait for ALL to complete
      ↓
Stage 3: build-and-bundle
  └─ ... and so on
```

### Key Rules:
- Stages run in the order defined
- All jobs in a stage run in parallel (by default)
- Next stage starts only when ALL jobs in current stage complete
- If any job fails, the pipeline stops (unless configured otherwise)

---

## Jobs

### Anatomy of a Job

```yaml
validate:infrastructure:           # Job name
  stage: validate                  # Which stage it belongs to
  <<: *node_setup                  # Template to inherit from
  tags:                            # Runner requirements
    - arch:amd64
    - size:medium
  script:                          # Commands to execute
    - cd infrastructure
    - npm ci
    - npm run build
  cache:                           # Files to cache between runs
    key: infrastructure-deps
    paths:
      - infrastructure/node_modules/
  artifacts:                       # Files to pass to next jobs
    paths:
      - infrastructure/cdk.out/
    expire_in: 1 hour
```

### Job Lifecycle:
1. **Setup**: Pull image, start container
2. **before_script**: Run setup commands (from template)
3. **script**: Run main job commands
4. **after_script**: Cleanup (if defined)
5. **Teardown**: Save artifacts, destroy container

---

## Variables

### Global Variables
```yaml
variables:
  AWS_CREDS_TARGET_ROLE: arn:aws:iam::210490146110:role/GitLab
  AWS_DEFAULT_REGION: us-east-1
  PYTHON_VERSION: "3.13"
  NODE_VERSION: "18"
```

**Available to**: All jobs in the pipeline
**Use case**: Configuration that doesn't change between jobs

### Job-Level Variables
```yaml
deploy:infrastructure:
  variables:
    AWS_CREDS_TARGET_ROLE: arn:aws:iam::210490146110:role/GitLab
    AWS_DEFAULT_REGION: us-east-1
```

**Available to**: Only this specific job
**Use case**: Override global variables or add job-specific config

### How to use in scripts:
```bash
echo "Deploying to region: $AWS_DEFAULT_REGION"
ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
```

---

## Templates and Anchors

### YAML Anchors (Reusable Templates)

```yaml
.aws_setup: &aws_setup              # Define template with anchor
  image: public.ecr.aws/docker/library/python:3.13-slim
  before_script:
    - apt-get update -qq
    - pip3 install awscli boto3
    - aws --version

deploy:infrastructure:
  <<: *aws_setup                    # Use template with alias
  stage: deploy-infrastructure
  script:
    - npx cdk deploy --all
```

### What happens:
The `<<: *aws_setup` expands to:
```yaml
deploy:infrastructure:
  image: public.ecr.aws/docker/library/python:3.13-slim
  before_script:
    - apt-get update -qq
    - pip3 install awscli boto3
    - aws --version
  stage: deploy-infrastructure
  script:
    - npx cdk deploy --all
```

### Benefits:
- **DRY principle**: Don't repeat yourself
- **Consistency**: All AWS jobs use same setup
- **Maintainability**: Change once, applies everywhere

### Our Templates:
1. `.aws_setup`: Python + AWS CLI for deployment jobs
2. `.python_setup`: Python environment for testing/bundling
3. `.node_setup`: Node.js environment for frontend

---

## Scripts

### Single Command
```yaml
script:
  - npm install
```

### Multiple Commands
```yaml
script:
  - cd infrastructure
  - npm ci
  - npm run build
  - npx cdk synth --all
```

### Multi-line Scripts (Bash)
```yaml
script:
  - |
    for agent in orchestrator-agent impact-assessment-agent; do
      echo "Processing $agent..."
      cd $agent
      python3 -m pytest tests/
      cd ..
    done
```

### Key Points:
- Each line is a separate command
- If any command fails (exit code ≠ 0), job fails
- Use `||` for optional commands: `npm run lint || true`
- Multi-line scripts (`|`) are useful for loops and complex logic

---

## Tags

```yaml
tags:
  - arch:amd64
  - size:medium
```

### What are tags?
Tags specify which GitLab Runner should execute the job.

### How it works:
1. GitLab Runners register with tags (e.g., "I'm an amd64 runner with medium resources")
2. Jobs specify required tags
3. GitLab matches jobs to runners with matching tags

### Common Tag Patterns:

**Architecture**:
- `arch:amd64` - x86_64 architecture
- `arch:arm64` - ARM architecture

**Size/Resources**:
- `size:small` - 1 CPU, 2GB RAM
- `size:medium` - 2 CPU, 4GB RAM
- `size:large` - 4 CPU, 8GB RAM

**Environment**:
- `env:production`
- `env:staging`

### Why we use them:
- **Bundling jobs**: Need `size:large` for CPU-intensive pip installs
- **Most jobs**: Use `size:medium` for balance
- **Architecture**: Ensure x86_64 for Lambda compatibility

---

## Dependencies and Needs

### Dependencies (Old Way)
```yaml
deploy:frontend:
  dependencies:
    - build:frontend
```

**Behavior**: 
- Downloads artifacts from specified jobs
- Still waits for ALL jobs in previous stages to complete

### Needs (Modern Way)
```yaml
deploy:frontend:
  needs:
    - job: build:frontend
      artifacts: true
    - job: deploy:infrastructure
```

**Behavior**:
- Downloads artifacts from `build:frontend`
- Starts as soon as both jobs complete
- **Doesn't wait** for other jobs in previous stages

### Visual Comparison:

**Without needs** (Sequential):
```
Stage 1: Build
  ├─ build:frontend (5 min) ✓
  ├─ bundle:agents (10 min) ✓
  └─ bundle:lambdas (8 min) ✓
      ↓ (waits for ALL)
Stage 2: Deploy
  └─ deploy:frontend (starts after 10 min)
```

**With needs** (Parallel):
```
Stage 1: Build
  ├─ build:frontend (5 min) ✓
  |     ↓ (starts immediately)
  |  deploy:frontend (starts after 5 min)
  |
  ├─ bundle:agents (10 min) ✓
  └─ bundle:lambdas (8 min) ✓
```

### Our Usage:
```yaml
deploy:frontend:
  needs:
    - job: build:frontend        # Need frontend artifacts
      artifacts: true
    - job: deploy:infrastructure # Need infrastructure ready
```

This means: "Start frontend deployment as soon as frontend is built AND infrastructure is deployed, don't wait for agent bundling"

---

## Artifacts

### What are artifacts?
Files produced by a job that need to be passed to other jobs.

### Example:
```yaml
build:frontend:
  script:
    - npm run build
  artifacts:
    paths:
      - frontend-spa/dist/      # Save this directory
    expire_in: 1 day            # Delete after 1 day
```

### How it works:
1. Job completes successfully
2. GitLab zips specified paths
3. Uploads to GitLab storage
4. Other jobs can download these artifacts

### Downloading artifacts:
```yaml
deploy:frontend:
  needs:
    - job: build:frontend
      artifacts: true           # Download artifacts
  script:
    - ls frontend-spa/dist/     # Files are available!
```

### Best Practices:
- **Only save what's needed**: Artifacts cost storage
- **Set expiration**: `expire_in: 1 day` cleans up automatically
- **Use for**: Build outputs, test reports, deployment packages

### Our Artifacts:
1. **Frontend build**: `frontend-spa/dist/` → Deploy to S3
2. **Lambda bundles**: `*.zip` files → Upload to S3
3. **Agent packages**: `deployment.zip` → Upload to S3
4. **CDK synth**: `cdk.out/` → Validate infrastructure

---

## Cache

### What is cache?
Stores dependencies between pipeline runs to speed up jobs.

### Example:
```yaml
validate:frontend:
  script:
    - npm ci
  cache:
    key: frontend-deps          # Unique identifier
    paths:
      - frontend-spa/node_modules/
```

### How it works:

**First run**:
1. Cache miss (no cached files)
2. Run `npm ci` (downloads all packages - slow)
3. Save `node_modules/` to cache

**Second run**:
1. Cache hit (cached files found)
2. Restore `node_modules/` from cache
3. Run `npm ci` (much faster, only updates changed packages)

### Cache vs Artifacts:

| Feature | Cache | Artifacts |
|---------|-------|-----------|
| Purpose | Speed up jobs | Pass files between jobs |
| Scope | Same job across runs | Different jobs in same run |
| Reliability | Best effort (may miss) | Guaranteed |
| Storage | Temporary | Persistent (until expiry) |
| Use for | Dependencies | Build outputs |

### Cache Keys:
```yaml
cache:
  key: frontend-deps            # Static key
  # OR
  key: ${CI_COMMIT_REF_SLUG}    # Per-branch cache
  # OR
  key: 
    files:
      - package-lock.json       # Cache invalidates when file changes
```

### Our Cache Strategy:
- **Frontend**: Cache `node_modules/` with key `frontend-deps`
- **Infrastructure**: Cache `node_modules/` with key `infrastructure-deps`
- **Why**: npm install is slow, caching saves 2-3 minutes per job

---

## Conditional Execution

### only/except (Simple)
```yaml
build:frontend:
  only:
    - main
    - develop
```

**Meaning**: Only run this job for `main` and `develop` branches

### rules (Advanced)
```yaml
deploy:production:
  rules:
    - if: '$CI_COMMIT_BRANCH == "main"'
      when: manual
    - if: '$CI_COMMIT_TAG'
      when: on_success
    - when: never
```

**Meaning**: 
- If branch is `main`: Run manually
- If it's a tag: Run automatically
- Otherwise: Never run

### Common Conditions:

**Branch-based**:
```yaml
only:
  - main              # Only main branch
  - /^release-.*$/    # Any branch starting with "release-"
```

**Tag-based**:
```yaml
only:
  - tags              # Only when pushing tags
```

**Change-based**:
```yaml
only:
  changes:
    - frontend-spa/**/*   # Only if frontend files changed
```

### Our Usage:
```yaml
only:
  - main
  - develop
```

**Why**: 
- Bundling and deployment only for main/develop branches
- Feature branches only run validation and tests
- Saves resources and time

---

## Manual Jobs

### Automatic vs Manual

**Automatic** (default):
```yaml
test:frontend:
  script:
    - npm test
```
Runs automatically when stage starts

**Manual**:
```yaml
deploy:infrastructure:
  when: manual
  script:
    - npx cdk deploy --all
```
Requires human to click "Play" button in GitLab UI

### Why use manual jobs?

1. **Safety**: Prevent accidental deployments
2. **Cost**: Avoid unnecessary AWS charges
3. **Control**: Deploy when ready, not automatically
4. **Approval**: Require human review before critical actions

### Our Manual Jobs:
- `deploy:infrastructure` - Deploys AWS resources
- `deploy:agents:upload-to-s3` - Uploads agent code
- `deploy:agents:update-runtimes` - Updates running agents
- `deploy:frontend` - Deploys to production
- `verify:*` - Verification tests

### Manual Job Flow:
```
Pipeline starts automatically
  ↓
Validate → Test → Build (all automatic)
  ↓
Deploy Infrastructure (⏸️ PAUSED - waiting for manual trigger)
  ↓ (click Play button)
Deploy continues...
```

---

## Advanced Concepts

### allow_failure
```yaml
verify:e2e:
  script:
    - python3 test_e2e.py
  allow_failure: true
```

**Meaning**: Job can fail without stopping the pipeline
**Use case**: Optional tests, experimental features

### retry
```yaml
deploy:frontend:
  script:
    - aws s3 sync dist/ s3://bucket/
  retry:
    max: 2
    when:
      - runner_system_failure
      - stuck_or_timeout_failure
```

**Meaning**: Retry job up to 2 times on specific failures
**Use case**: Network issues, temporary AWS API failures

### timeout
```yaml
test:long-running:
  script:
    - npm run test:integration
  timeout: 2h
```

**Meaning**: Kill job if it runs longer than 2 hours
**Use case**: Prevent stuck jobs from blocking pipeline

### coverage
```yaml
test:frontend:
  script:
    - npm test
  coverage: '/All files[^|]*\|[^|]*\s+([\d\.]+)/'
```

**Meaning**: Extract coverage percentage from output
**Use case**: Display test coverage in GitLab UI

---

## Pipeline Execution Flow

### Complete Example:

```
1. Commit pushed to main branch
   ↓
2. GitLab creates pipeline
   ↓
3. STAGE: validate (5 jobs run in parallel)
   ├─ validate:infrastructure ✓
   ├─ validate:frontend ✓
   ├─ validate:python-agents ✓
   ├─ validate:mcp-servers ✓
   └─ All complete
   ↓
4. STAGE: test (6 jobs run in parallel)
   ├─ test:frontend ✓
   ├─ test:erp-data-mcp ✓
   ├─ test:capacity-optimization-agent ✓
   ├─ test:constraint-matching-agent ✓
   ├─ test:impact-assessment-agent ✓
   ├─ test:orchestrator-agent ✓
   └─ All complete
   ↓
5. STAGE: build-and-bundle (3 jobs run in parallel)
   ├─ build:frontend ✓ (5 min)
   ├─ bundle:mcp-lambdas ✓ (8 min)
   ├─ bundle:agent-packages ✓ (10 min)
   └─ All complete
   ↓
6. STAGE: deploy-infrastructure (manual)
   └─ ⏸️ Waiting for manual trigger...
   ↓ (user clicks Play)
   └─ deploy:infrastructure ✓ (15 min)
   ↓
7. STAGE: deploy-agents (manual, sequential)
   └─ ⏸️ Waiting for manual trigger...
   ↓ (user clicks Play)
   ├─ deploy:agents:upload-to-s3 ✓ (2 min)
   └─ deploy:agents:update-runtimes ✓ (5 min)
   
8. STAGE: deploy-frontend (manual, parallel with agents)
   └─ ⏸️ Waiting for manual trigger...
   ↓ (user clicks Play)
   └─ deploy:frontend ✓ (3 min)
   ↓
9. STAGE: verify (manual)
   └─ ⏸️ Waiting for manual trigger...
   ↓ (user clicks Play)
   ├─ verify:infrastructure ✓
   └─ verify:e2e ✓
   ↓
10. Pipeline complete! ✓
```

---

## Best Practices from Our Pipeline

### 1. Use Templates for Consistency
```yaml
.aws_setup: &aws_setup
  image: python:3.13-slim
  before_script:
    - pip install awscli boto3
```

### 2. Optimize with Parallel Execution
```yaml
# All these run at the same time
build:frontend:
  stage: build-and-bundle
bundle:mcp-lambdas:
  stage: build-and-bundle
bundle:agent-packages:
  stage: build-and-bundle
```

### 3. Use needs for Smart Dependencies
```yaml
deploy:frontend:
  needs:
    - job: build:frontend
      artifacts: true
    - job: deploy:infrastructure
```

### 4. Cache Dependencies
```yaml
cache:
  key: frontend-deps
  paths:
    - node_modules/
```

### 5. Set Artifact Expiration
```yaml
artifacts:
  paths:
    - dist/
  expire_in: 1 day
```

### 6. Manual Deployments for Safety
```yaml
deploy:production:
  when: manual
```

### 7. Use Appropriate Runner Sizes
```yaml
tags:
  - size:large    # For CPU-intensive bundling
  - size:medium   # For most jobs
```

---

## Common Troubleshooting

### Job Stuck in Pending
**Cause**: No runner with matching tags available
**Solution**: Check tags match available runners

### Artifacts Not Found
**Cause**: Job didn't produce artifacts or expired
**Solution**: Check `artifacts.paths` and `expire_in`

### Cache Not Working
**Cause**: Cache key changed or cache cleared
**Solution**: Use stable cache keys, check cache settings

### Job Fails Immediately
**Cause**: Image pull failure or before_script error
**Solution**: Check image name and before_script commands

### Pipeline Slow
**Cause**: Sequential execution, no caching
**Solution**: Use `needs`, enable caching, parallelize jobs

---

## Summary

Our pipeline demonstrates:
- ✅ **Modular design** with reusable templates
- ✅ **Parallel execution** for speed
- ✅ **Smart dependencies** with needs
- ✅ **Caching** for faster builds
- ✅ **Manual gates** for safety
- ✅ **Proper resource allocation** with tags
- ✅ **Artifact management** for efficiency

This creates a fast, reliable, and safe CI/CD pipeline for your multi-component AWS application!


---

## GitLab Runners - Deep Dive

### Are We Using a Separate Runner for Each Job?

**Short Answer**: Not necessarily. It depends on your GitLab Runner configuration.

### How GitLab Runners Work

#### Runner Pool Concept
```
GitLab Instance
    |
    v
Runner Pool (Multiple Runners with tags: arch:amd64, size:medium)
    |
    +-- Runner 1 (idle)
    +-- Runner 2 (running job A)
    +-- Runner 3 (running job B)
    +-- Runner 4 (idle)
    +-- Runner 5 (running job C)
```

### Job Assignment Process

When a job needs to run:

1. **Job enters queue** with its tag requirements:
   ```yaml
   test:frontend:
     tags:
       - arch:amd64
       - size:medium
   ```

2. **GitLab searches for available runner** that matches ALL tags:
   - Has tag `arch:amd64`? ✓
   - Has tag `size:medium`? ✓
   - Is currently idle? ✓

3. **Job assigned to first matching idle runner**

4. **Runner executes the job**:
   - Pulls Docker image
   - Creates container
   - Runs the job
   - Destroys container
   - Becomes idle again

5. **Runner is now available** for the next job

### Parallel Job Execution

When multiple jobs run in parallel (same stage):

```
Stage: test (6 jobs need to run)

Scenario 1: 6+ Runners Available
├─ Job 1 → Runner A
├─ Job 2 → Runner B
├─ Job 3 → Runner C
├─ Job 4 → Runner D
├─ Job 5 → Runner E
└─ Job 6 → Runner F
All jobs run simultaneously ✓

Scenario 2: Only 3 Runners Available
├─ Job 1 → Runner A
├─ Job 2 → Runner B
├─ Job 3 → Runner C
└─ Jobs 4, 5, 6 wait in queue...
    ↓ (Runner A finishes Job 1)
├─ Job 4 → Runner A
    ↓ (Runner B finishes Job 2)
├─ Job 5 → Runner B
    ↓ (Runner C finishes Job 3)
└─ Job 6 → Runner C
```

### Runner Types

#### 1. Shared Runners (Most Common)
```
Multiple projects share a pool of runners
Project A Job 1 → Runner 1
Project B Job 1 → Runner 2
Project A Job 2 → Runner 1 (after Job 1 completes)
```

**Characteristics**:
- Shared across all projects in GitLab instance
- Managed by GitLab administrators
- May have concurrency limits per project
- Cost-effective but may have queuing

#### 2. Group Runners
```
Multiple projects in a group share runners
Group "Engineering"
  ├─ Project A → Runner Pool
  └─ Project B → Runner Pool
```

**Characteristics**:
- Shared within a GitLab group
- More control than shared runners
- Better resource allocation for team

#### 3. Project-Specific Runners
```
Dedicated runners for one project only
Your Project → Your Dedicated Runners
```

**Characteristics**:
- Exclusive to your project
- No queuing from other projects
- More expensive but guaranteed availability
- Full control over configuration

### Our Pipeline's Runner Usage

Looking at our pipeline:

```yaml
validate:infrastructure:
  tags:
    - arch:amd64
    - size:medium

test:frontend:
  tags:
    - arch:amd64
    - size:medium

bundle:mcp-lambdas:
  tags:
    - arch:amd64
    - size:large
```

### What Actually Happens:

#### Stage 1: Validate (5 jobs in parallel)
```
If 5+ runners with [arch:amd64, size:medium] are available:
├─ validate:infrastructure → Runner A
├─ validate:frontend → Runner B
├─ validate:python-agents → Runner C
├─ validate:mcp-servers → Runner D
└─ All run simultaneously

If only 2 runners available:
├─ validate:infrastructure → Runner A
├─ validate:frontend → Runner B
├─ validate:python-agents → (waiting...)
├─ validate:mcp-servers → (waiting...)
    ↓ (Runner A finishes)
├─ validate:python-agents → Runner A
    ↓ (Runner B finishes)
└─ validate:mcp-servers → Runner B
```

#### Stage 3: Build-and-Bundle (Mixed sizes)
```
Jobs with different size requirements:
├─ build:frontend [size:medium] → Runner A (medium)
├─ bundle:mcp-lambdas [size:large] → Runner B (large)
└─ bundle:agent-packages [size:large] → Runner C (large)

Note: size:medium and size:large are different runner pools!
```

### Runner Reuse Within Pipeline

**Important**: The same runner can execute multiple jobs from your pipeline:

```
Your Pipeline Run:
├─ Job 1 (validate:infrastructure) → Runner A
    ↓ (completes, Runner A becomes idle)
├─ Job 2 (test:frontend) → Runner A (reused!)
    ↓ (completes, Runner A becomes idle)
└─ Job 3 (build:frontend) → Runner A (reused again!)
```

**Why this is safe**:
- Each job runs in a fresh Docker container
- Container is destroyed after job completes
- No state persists between jobs (except cache/artifacts)
- Complete isolation guaranteed

### Concurrency Limits

GitLab can limit concurrent jobs per project:

```yaml
# GitLab instance settings (not in your .gitlab-ci.yml)
Shared Runners: 10 concurrent jobs per project
Group Runners: 20 concurrent jobs per project
Project Runners: Unlimited (depends on your runners)
```

**Impact on our pipeline**:
```
If limit is 3 concurrent jobs:

Stage: test (6 jobs)
├─ Job 1, 2, 3 run immediately
└─ Job 4, 5, 6 wait in queue
    ↓ (as jobs complete)
    Jobs 4, 5, 6 start running
```

### How to Check Your Runner Configuration

#### In GitLab UI:
1. Go to: Settings → CI/CD → Runners
2. You'll see:
   - Available shared runners
   - Available group runners
   - Project-specific runners
   - Tags for each runner
   - Current status (idle/running)

#### Runner Information Shows:
```
Runner #12345
├─ Tags: arch:amd64, size:medium, docker
├─ Status: Running job #67890
├─ Executor: docker
└─ Concurrent jobs: 1
```

### Optimizing Runner Usage

#### 1. Match Job Requirements to Runner Availability
```yaml
# If you have many small runners but few large ones:
bundle:agent-packages:
  tags:
    - arch:amd64
    - size:large    # May queue longer
```

#### 2. Use Appropriate Sizes
```yaml
# Don't request large runner for simple tasks
validate:infrastructure:
  tags:
    - size:medium   # Sufficient for npm ci
    
# Do request large runner for CPU-intensive tasks
bundle:mcp-lambdas:
  tags:
    - size:large    # Needed for pip install with compilation
```

#### 3. Consider Job Duration
```yaml
# Long-running jobs block runners
test:e2e:
  tags:
    - size:medium
  timeout: 30m      # Don't let it run forever
```

### Cost Implications

#### Shared Runners (GitLab.com)
- Free tier: 400 CI/CD minutes per month
- Paid tier: Additional minutes charged
- **Our pipeline**: ~25 minutes per run
- **Monthly runs**: ~16 runs on free tier

#### Self-Hosted Runners
- You manage the infrastructure
- Pay for compute resources (EC2, etc.)
- Unlimited CI/CD minutes
- More control but more maintenance

### Best Practices for Runner Usage

#### 1. Use Specific Tags
```yaml
# Good: Specific requirements
tags:
  - arch:amd64
  - size:medium
  - docker

# Bad: Too generic (may match wrong runner)
tags:
  - linux
```

#### 2. Don't Over-Request Resources
```yaml
# Bad: Wastes large runner on simple task
validate:frontend:
  tags:
    - size:large    # Overkill for npm ci

# Good: Right-sized
validate:frontend:
  tags:
    - size:medium   # Sufficient
```

#### 3. Balance Parallelism
```yaml
# If you have limited runners, consider:
# - Reducing parallel jobs
# - Splitting large jobs into smaller ones
# - Using needs to optimize execution order
```

### Monitoring Runner Usage

#### Check Pipeline Efficiency:
```
Pipeline Duration: 25 minutes
Total Job Time: 45 minutes
Efficiency: 55% (some jobs waited for runners)

Ideal: Pipeline Duration ≈ Longest Job Duration
Reality: Often longer due to runner availability
```

#### Signs of Runner Shortage:
- Jobs stuck in "pending" state
- Long gaps between stage completions
- Pipeline duration >> sum of job durations

### Summary: Runner Usage in Our Pipeline

**What we specify**:
```yaml
tags:
  - arch:amd64      # x86_64 architecture
  - size:medium     # 2 CPU, 4GB RAM
  # OR
  - size:large      # 4 CPU, 8GB RAM
```

**What GitLab does**:
1. Finds available runner matching tags
2. Assigns job to that runner
3. Runner may execute multiple jobs from your pipeline
4. Each job runs in isolated container
5. Runner becomes available for next job after completion

**Key Points**:
- ✅ Runners are reused across jobs (safe due to containerization)
- ✅ Multiple jobs can run on same runner (sequentially)
- ✅ Parallel jobs may use different runners (if available)
- ✅ Same runner can serve multiple projects (shared runners)
- ✅ Each job gets fresh, isolated environment

**Bottom Line**: You don't get a dedicated runner per job. Runners are shared resources from a pool, assigned dynamically based on availability and tag matching. This is efficient and cost-effective while maintaining complete isolation between jobs.
