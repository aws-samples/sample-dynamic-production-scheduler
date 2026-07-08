# Logical Components — Unit 8: Frontend

## Overview

The frontend is a static SPA with no server-side runtime. Logical components are browser-side modules and external infrastructure services.

## Client-Side Logical Components

### 1. WebSocket Client Module
- Manages connection lifecycle (connect, disconnect, reconnect)
- Exponential backoff reconnection (Pattern 3)
- Dispatches incoming ServerMessages to Zustand store actions
- Sends ClientMessages (user_message, order_decision)
- Exposes connection status to UI

### 2. Zustand Store
- Single store with named slices: session, connection, chat, sidePanel, capacity, audit
- Selective subscriptions per component (Pattern 1)
- Actions: sendMessage, sendDecision, appendStreamToken, setPhase, updateCapacity, setPendingDecision, showDetail, closeDetail, addAuditEntry

### 3. Markdown Sanitization Module
- react-markdown + rehype-sanitize pipeline (Pattern 5)
- Allowlist of safe HTML elements
- Shared across all ChatMessage components

### 4. Logging Utility
- Structured console logging (Pattern 8)
- Environment-aware (dev vs prod log levels)
- No PII in output

### 5. Error Boundary Components
- AppErrorBoundary (top-level)
- ChatPanelBoundary (chat isolation)
- SidePanelBoundary (panel isolation)
- Each logs error and renders fallback UI (Pattern 2)

## Infrastructure Logical Components

### 6. S3 Bucket (Static Hosting)
- Stores built SPA assets (HTML, JS, CSS, images)
- Private bucket — access only via CloudFront OAI
- Versioned deployments via content-hash filenames

### 7. CloudFront Distribution
- CDN edge caching for global low-latency delivery
- HTTPS termination with ACM certificate
- Response Headers Policy for security headers (Pattern 4)
- Default root object: `index.html`
- SPA routing: custom error response 403/404 -> `/index.html` with 200 status

### 8. WebSocket API Gateway
- Managed by Infrastructure unit (Unit 9)
- Frontend connects to `wss://{api-id}.execute-api.{region}.amazonaws.com/{stage}`
- Routes: $connect, $disconnect, $default
- Frontend is a consumer — no infrastructure ownership

## Component Interaction

```
+-------------------+     +-------------------+     +-------------------+
| CloudFront (CDN)  | --> | S3 Bucket         |     | API Gateway (WS)  |
| - HTTPS           |     | - SPA assets      |     | - wss:// endpoint |
| - Security headers|     | - index.html      |     | - $connect route  |
| - SPA routing     |     | - JS/CSS bundles  |     | - $default route  |
+-------------------+     +-------------------+     +-------------------+
        |                                                    |
        | HTTPS (static assets)                              | WSS (streaming)
        v                                                    v
+-------------------------------------------------------------------+
|                        Browser Runtime                            |
|                                                                   |
|  +------------------+  +------------------+  +------------------+ |
|  | WebSocket Client |  | Zustand Store    |  | Error Boundaries | |
|  | (connect/send/   |  | (state slices,   |  | (App, Chat,      | |
|  |  reconnect)      |  |  actions)        |  |  SidePanel)      | |
|  +------------------+  +------------------+  +------------------+ |
|                                                                   |
|  +------------------+  +------------------+                       |
|  | Markdown Sanitize|  | Logging Utility  |                       |
|  | (react-markdown  |  | (structured      |                       |
|  |  + rehype)       |  |  console)        |                       |
|  +------------------+  +------------------+                       |
+-------------------------------------------------------------------+
```

## Dependency Map

| Component | Depends On | Depended By |
|-----------|-----------|-------------|
| WebSocket Client | Zustand Store (dispatch actions) | MessageInput, ConnectionIndicator |
| Zustand Store | — (standalone) | All UI components |
| Markdown Sanitize | react-markdown, rehype-sanitize | ChatMessage |
| Logging Utility | — (standalone) | WebSocket Client, Error Boundaries |
| Error Boundaries | Logging Utility | App (wraps panels) |
| S3 Bucket | — | CloudFront |
| CloudFront | S3 Bucket, ACM Certificate | Browser (serves assets) |
| API Gateway WS | Backend ECS (Unit 9) | WebSocket Client |
