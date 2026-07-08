# DisruptionAI Infrastructure (CDK)

> **⚠️ Note:** This is a demo/sample component, not intended for production use without security review.

AWS CDK TypeScript project provisioning all infrastructure for the DisruptionAI production scheduling platform.

## Stacks

| Stack | Purpose |
|---|---|
| DatabaseStack | 7 DynamoDB tables (orders, capacity, workforce, materials, customers, tracker, audit) |
| MonitoringStack | CloudWatch log groups (90-day retention), dashboard, alarms, metric filters |
| FrontendStack | S3 + CloudFront SPA hosting with security headers |
| WebSocketStack | API Gateway WebSocket API for real-time orchestrator updates |
| IamStack | Least-privilege IAM roles for ECS tasks (MCP servers + agents) |

## Prerequisites

- Node.js 18+
- AWS CDK CLI: `npm install -g aws-cdk`
- AWS credentials configured

## Commands

```bash
npm install          # Install dependencies
npm test             # Run unit tests (34 tests)
npx cdk synth        # Synthesize CloudFormation templates
npx cdk diff         # Preview changes
npx cdk deploy --all # Deploy all stacks
npx cdk destroy --all # Tear down all stacks
```

## Stack Dependencies

```
DatabaseStack
  └─> MonitoringStack
  └─> IamStack (needs table ARNs)
        └─> WebSocketStack (needs task role ARN)
              └─> FrontendStack (needs WebSocket URL)
```

## Security Compliance

- SECURITY-01: DynamoDB AWS-managed encryption, S3 SSE-S3, TLS enforced
- SECURITY-02: CloudFront access logging, API Gateway execution logging
- SECURITY-04: CSP, HSTS, X-Content-Type-Options, X-Frame-Options, Referrer-Policy
- SECURITY-06: Least-privilege IAM — specific actions and resource ARNs, no wildcards
- SECURITY-07: S3 public access blocked, no open inbound rules
- SECURITY-09: No default credentials, no public buckets
- SECURITY-10: Pinned dependency versions in package.json
- SECURITY-14: 90-day log retention, roles cannot delete own logs
