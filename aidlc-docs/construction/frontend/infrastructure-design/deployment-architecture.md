# Deployment Architecture — Unit 8: Frontend

## Build Pipeline

```
Source Code (frontend-spa/)
  |
  | pnpm install
  v
Dependencies Installed
  |
  | pnpm run build (vite build)
  v
dist/
  +-- index.html
  +-- assets/
        +-- index-[hash].js
        +-- index-[hash].css
        +-- vendor-[hash].js
  |
  | aws s3 sync dist/ s3://disruptionai-frontend-{env}-${AWS::AccountId}/
  v
S3 Bucket Updated
  |
  | aws cloudfront create-invalidation --paths "/*"
  v
CloudFront Cache Invalidated
  |
  v
Live at https://disruptionai.{domain}
```

## Deployment Steps

1. Install dependencies: `pnpm install --frozen-lockfile`
2. Build: `VITE_WS_URL=wss://... pnpm run build`
3. Upload to S3: `aws s3 sync dist/ s3://disruptionai-frontend-{env}-${AWS::AccountId}/ --delete`
4. Invalidate CloudFront: `aws cloudfront create-invalidation --distribution-id {id} --paths "/*"`

## Architecture Diagram

```
+-------------------+
|  Developer / CI   |
+-------------------+
         |
         | S3 sync + CF invalidation
         v
+-------------------+     +-------------------+
| S3 Bucket         |<----| CloudFront (CDN)  |
| - index.html      |     | - HTTPS           |
| - assets/*.js     |     | - Security headers|
| - assets/*.css    |     | - SPA routing     |
| (private, OAI)    |     | - Cache policy    |
+-------------------+     +-------------------+
                                   |
                                   | HTTPS
                                   v
                          +-------------------+
                          | Browser           |
                          | - React SPA       |
                          | - Zustand store   |
                          | - WebSocket client|
                          +-------------------+
                                   |
                                   | WSS
                                   v
                          +-------------------+
                          | API Gateway WS    |
                          | (Unit 9 owned)    |
                          +-------------------+
```

## Rollback Strategy

- S3 versioning enabled — previous versions recoverable
- CloudFront invalidation takes 1-2 minutes
- Rollback: re-sync previous build artifacts to S3 + invalidate
- No database migrations — pure static assets

## Environment Strategy

| Environment | S3 Bucket | CloudFront | WS Endpoint |
|-------------|-----------|------------|-------------|
| dev | disruptionai-frontend-dev-${AWS::AccountId} | Dev distribution | Dev API GW |
| prod | disruptionai-frontend-prod-${AWS::AccountId} | Prod distribution | Prod API GW |
