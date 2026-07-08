# Security Test Instructions — DisruptionAI

## Purpose

Validate compliance with all 15 SECURITY rules defined in the Security Baseline extension.

## Test 1: Dependency Vulnerability Scan (SECURITY-10)

```bash
# Python dependencies
source /tmp/disruptionai-venv/bin/activate
pip install pip-audit
pip-audit

# Frontend dependencies
cd frontend-spa && npm audit && cd ..

# Infrastructure dependencies
cd infrastructure && npm audit && cd ..
```

**Pass criteria**: No critical or high severity vulnerabilities

## Test 2: IAM Least-Privilege Verification (SECURITY-06)

```bash
cd infrastructure
npx cdk synth

# Inspect IAM policies in synthesized templates
# Verify no wildcard actions (*) or wildcard resources (*)
grep -r '"Action"' cdk.out/ | grep -c '"\\*"'
# Expected: 0 matches

# Verify specific resource ARNs (not *)
grep -r '"Resource"' cdk.out/ | grep -c '"\\*"'
# Expected: 0 matches (all resources should be specific ARNs)
```

**Pass criteria**: Zero wildcard actions, zero wildcard resources

## Test 3: S3 Public Access Block (SECURITY-09)

```bash
# After deployment, verify public access is blocked
aws s3api get-public-access-block \
  --bucket disruptionai-frontend-$(aws sts get-caller-identity --query Account --output text)
```

**Pass criteria**: All four block settings are `true`

## Test 4: CloudFront Security Headers (SECURITY-04)

```bash
# After deployment, curl the CloudFront distribution
DIST_URL=$(aws cloudformation describe-stacks \
  --stack-name DisruptionAI-Frontend \
  --query "Stacks[0].Outputs[?ExportName=='disruptionai-frontend-url'].OutputValue" \
  --output text)

curl -sI "$DIST_URL" | grep -iE "content-security-policy|strict-transport|x-content-type|x-frame|referrer-policy"
```

**Expected headers**:
- `Content-Security-Policy: default-src 'self'; connect-src 'self' wss://...`
- `Strict-Transport-Security: max-age=31536000; includeSubDomains`
- `X-Content-Type-Options: nosniff`
- `X-Frame-Options: DENY`
- `Referrer-Policy: strict-origin-when-cross-origin`

**Pass criteria**: All 5 headers present with correct values

## Test 5: Encryption at Rest (SECURITY-01)

```bash
# Verify DynamoDB tables have encryption
for TABLE in orders capacity manpower materials customers tracker audit; do
  echo "disruptionai-$TABLE:"
  aws dynamodb describe-table --table-name "disruptionai-$TABLE" \
    --query "Table.SSEDescription.Status" --output text
done

# Verify S3 bucket encryption
BUCKET="disruptionai-frontend-$(aws sts get-caller-identity --query Account --output text)"
aws s3api get-bucket-encryption --bucket "$BUCKET" \
  --query "ServerSideEncryptionConfiguration.Rules[0].ApplyServerSideEncryptionByDefault.SSEAlgorithm"
```

**Pass criteria**: All DynamoDB tables show `ENABLED`, S3 shows `AES256`

## Test 6: Access Logging Enabled (SECURITY-02)

```bash
# CloudFront logging
DIST_ID=$(aws cloudformation describe-stacks \
  --stack-name DisruptionAI-Frontend \
  --query "Stacks[0].Outputs[?ExportName=='disruptionai-distribution-id'].OutputValue" \
  --output text)
aws cloudfront get-distribution --id "$DIST_ID" \
  --query "Distribution.DistributionConfig.Logging.Enabled"

# API Gateway logging
API_ID=$(aws cloudformation describe-stacks \
  --stack-name DisruptionAI-WebSocket \
  --query "Stacks[0].Outputs[?ExportName=='disruptionai-websocket-api-id'].OutputValue" \
  --output text)
aws apigatewayv2 get-stage --api-id "$API_ID" --stage-name prod \
  --query "DefaultRouteSettings"
```

**Pass criteria**: CloudFront logging `true`, API Gateway stage has logging settings

## Test 7: Log Retention and Integrity (SECURITY-14)

```bash
# Verify 90-day retention on all log groups
for LG in erp-data-mcp audit-mcp impact-assessment-agent \
  capacity-optimization-agent constraint-matching-agent \
  orchestrator-agent websocket-api; do
  echo "/disruptionai/$LG:"
  aws logs describe-log-groups \
    --log-group-name-prefix "/disruptionai/$LG" \
    --query "logGroups[0].retentionInDays"
done

# Verify task role cannot delete log groups (check IAM policy)
cd infrastructure && npx cdk synth
grep -A5 "logs:DeleteLogGroup" cdk.out/*.template.json
# Expected: no matches (action not granted)
```

**Pass criteria**: All log groups show 90 days, no DeleteLogGroup in IAM policies

## Test 8: Input Validation (SECURITY-05)

```bash
# Test MCP tool with invalid input
python -c "
from erp_data_mcp.models.schemas import OrderQuery
try:
    OrderQuery(plant='<script>alert(1)</script>' * 100)
    print('FAIL: Should have rejected oversized/malicious input')
except Exception as e:
    print(f'PASS: Rejected invalid input: {type(e).__name__}')
"

# Test agent with empty input
python -c "
from pydantic import ValidationError
from orchestrator_agent.schemas import PlannerMessage
try:
    PlannerMessage(text='', session_id='not-a-uuid')
    print('FAIL: Should have rejected empty text and invalid UUID')
except ValidationError as e:
    print(f'PASS: Rejected invalid input ({e.error_count()} errors)')
"
```

**Pass criteria**: All invalid inputs rejected with validation errors

## Test 9: No Hardcoded Credentials (SECURITY-12)

```bash
# Scan all source files for potential secrets
grep -rn "password\|secret\|api_key\|token" \
  --include="*.py" --include="*.ts" --include="*.tsx" \
  erp-data-mcp/ audit-mcp/ impact-assessment-agent/ \
  capacity-optimization-agent/ constraint-matching-agent/ \
  orchestrator-agent/ frontend-spa/src/ infrastructure/lib/ \
  | grep -v "test" | grep -v "node_modules" | grep -v ".pyc" \
  | grep -v "# " | grep -v "//" | grep -v "schema"
```

**Pass criteria**: No hardcoded credential values found (variable names referencing secrets are OK if values come from environment)

## Test 10: Network Configuration (SECURITY-07)

```bash
# Verify no 0.0.0.0/0 inbound rules except CloudFront
cd infrastructure && npx cdk synth
grep -c "0.0.0.0/0" cdk.out/*.template.json
# Expected: Only in CloudFront-related resources (if any)
```

**Pass criteria**: No open inbound rules to compute or database resources

## Security Compliance Summary Template

```
| SECURITY Rule | Description | Status |
|---------------|-------------|--------|
| SECURITY-01 | Encryption at rest and in transit | PASS/FAIL |
| SECURITY-02 | Access logging on network intermediaries | PASS/FAIL |
| SECURITY-03 | Application-level structured logging | PASS/FAIL |
| SECURITY-04 | HTTP security headers | PASS/FAIL |
| SECURITY-05 | Input validation on all API parameters | PASS/FAIL |
| SECURITY-06 | Least-privilege access policies | PASS/FAIL |
| SECURITY-07 | Restrictive network configuration | PASS/FAIL |
| SECURITY-08 | Application-level access control | N/A (no auth for MVP) |
| SECURITY-09 | Security hardening / misconfiguration | PASS/FAIL |
| SECURITY-10 | Software supply chain security | PASS/FAIL |
| SECURITY-11 | Secure design principles | PASS/FAIL |
| SECURITY-12 | Authentication and credential management | PASS/FAIL |
| SECURITY-13 | Software and data integrity | PASS/FAIL |
| SECURITY-14 | Alerting and monitoring | PASS/FAIL |
| SECURITY-15 | Exception handling and fail-safe defaults | PASS/FAIL |
```
