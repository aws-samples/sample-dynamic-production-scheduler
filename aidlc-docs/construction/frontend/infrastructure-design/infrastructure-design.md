# Infrastructure Design — Unit 8: Frontend

## Overview

The frontend is a static SPA deployed to S3 with CloudFront as CDN. It has no server-side compute. The WebSocket API Gateway is owned by Unit 9 (Infrastructure) — the frontend is a consumer only.

## AWS Services

### S3 Bucket — Static Asset Hosting

| Property | Value |
|----------|-------|
| Bucket Name | `disruptionai-frontend-{env}` |
| Access | Private — CloudFront OAI only |
| Versioning | Enabled |
| Encryption | AES-256 (SSE-S3) |
| Public Access | Blocked (all 4 settings) |
| Lifecycle | No expiration (small static assets) |

Content:
- `index.html` — SPA entry point
- `assets/` — JS bundles, CSS, images (content-hashed filenames)

### CloudFront Distribution — CDN + HTTPS + Security Headers

| Property | Value |
|----------|-------|
| Origin | S3 bucket via OAI |
| Protocol | HTTPS only (redirect HTTP to HTTPS) |
| Certificate | ACM certificate (us-east-1) |
| Default Root Object | `index.html` |
| Price Class | PriceClass_100 (US, Canada, Europe) |
| Cache Policy | CachingOptimized for assets, CachingDisabled for index.html |

SPA Routing — Custom Error Responses:
- 403 -> `/index.html` with HTTP 200
- 404 -> `/index.html` with HTTP 200

Response Headers Policy (SECURITY-04):
- Content-Security-Policy: `default-src 'self'; connect-src 'self' wss://*.execute-api.*.amazonaws.com; style-src 'self' 'unsafe-inline'`
- Strict-Transport-Security: `max-age=31536000; includeSubDomains`
- X-Content-Type-Options: `nosniff`
- X-Frame-Options: `DENY`
- Referrer-Policy: `strict-origin-when-cross-origin`

### WebSocket API Gateway (Consumer — Owned by Unit 9)

The frontend connects to the WebSocket API Gateway endpoint. Infrastructure is defined in Unit 9. Frontend configuration:

| Property | Value |
|----------|-------|
| Env Variable | `VITE_WS_URL` |
| Format | `wss://{api-id}.execute-api.{region}.amazonaws.com/{stage}` |
| Protocol | WSS (TLS) |

### ACM Certificate

| Property | Value |
|----------|-------|
| Region | us-east-1 (required for CloudFront) |
| Domain | `disruptionai.{domain}` (or custom) |
| Validation | DNS validation |

## Environment Configuration

Frontend environment variables (injected at build time via Vite):

| Variable | Description | Example |
|----------|-------------|---------|
| `VITE_WS_URL` | WebSocket API Gateway endpoint | `wss://abc123.execute-api.us-east-1.amazonaws.com/prod` |
| `VITE_APP_TITLE` | Application title | `DisruptionAI` |

## Security Compliance

| Rule | Status | Implementation |
|------|--------|---------------|
| SECURITY-01 | Compliant | S3 encryption at rest (SSE-S3), HTTPS in transit |
| SECURITY-02 | Compliant | CloudFront access logging enabled to S3 log bucket |
| SECURITY-04 | Compliant | Response headers policy on CloudFront |
| SECURITY-06 | Compliant | OAI scoped to single S3 bucket, no wildcard policies |
| SECURITY-07 | N/A | No VPC/security groups for static hosting |
| SECURITY-09 | Compliant | S3 public access blocked, no directory listing |
| SECURITY-10 | Compliant | No `latest` tags — CDK pins construct versions |

## Cost Estimate (MVP/Demo)

| Service | Estimated Monthly Cost |
|---------|----------------------|
| S3 | < $1 (small static assets, low traffic) |
| CloudFront | < $1 (demo traffic, PriceClass_100) |
| ACM | Free |
| Total | < $2/month |
