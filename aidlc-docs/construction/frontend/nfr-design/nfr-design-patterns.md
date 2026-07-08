# NFR Design Patterns — Unit 8: Frontend

## Pattern 1: Selective Store Subscription (Performance)

Addresses: NFR-FE-01 (streaming latency < 200ms)

Zustand allows components to subscribe to specific state slices. During token streaming, only the active ChatMessage component re-renders — not the entire message list.

Implementation:
- `useStore(state => state.chat.messages[index])` for individual message components
- `useStore(state => state.capacity)` for CapacityTracker (isolated from chat updates)
- `useStore(state => state.sidePanel.mode)` for panel switching
- Avoid `useStore(state => state)` — always select minimal slice

## Pattern 2: React Error Boundary Hierarchy (Reliability)

Addresses: NFR-FE-03 (error boundaries), SECURITY-15 (fail-safe defaults)

Three-level error boundary strategy:

```
+---------------------------------------------------------------+
|  AppErrorBoundary (top-level)                                 |
|  - Catches unhandled render errors                            |
|  - Shows "Something went wrong" + reload button               |
|  - Logs error to console with component stack                 |
|                                                               |
|  +---------------------------+  +---------------------------+ |
|  | ChatPanelBoundary         |  | SidePanelBoundary         | |
|  | - Isolates chat crashes   |  | - Isolates panel crashes  | |
|  | - Side panel still works  |  | - Chat still works        | |
|  | - Shows retry button      |  | - Shows retry button      | |
|  +---------------------------+  +---------------------------+ |
+---------------------------------------------------------------+
```

Fail-safe behavior:
- On error: deny further interaction in crashed panel (fail closed)
- Retry button resets error boundary state
- Errors logged with component stack trace (console only for MVP)

## Pattern 3: Exponential Backoff Reconnection (Reliability)

Addresses: NFR-FE-03 (WebSocket reconnection), BR-FE-08

Custom hook `useWebSocket` encapsulates connection lifecycle:

```
Connect
  |
  v
Connected ---(disconnect)---> Reconnecting
                                   |
                                   | delay = min(1s * 2^attempt, 30s)
                                   v
                               Retry Connect
                                   |
                          +--------+--------+
                          |                 |
                       Success           Failure
                          |                 |
                          v                 v
                      Connected        Increment attempt
                      (reset attempt)  (loop back to delay)
```

State exposed to UI:
- `connection.status`: drives input disabled state and header indicator
- `connection.reconnectAttempt`: available for debugging (not displayed)
- Session ID preserved across reconnections (sent on each connect)

## Pattern 4: Content Security Policy via CloudFront (Security)

Addresses: NFR-FE-04 (SECURITY-04), SECURITY-09

Security headers set at CDN edge via CloudFront Response Headers Policy — not in application code. This ensures headers are present on every response including static assets.

Headers:
- CSP: `default-src 'self'; connect-src 'self' wss://*.amazonaws.com; style-src 'self' 'unsafe-inline'`
- HSTS: `max-age=31536000; includeSubDomains`
- X-Content-Type-Options: `nosniff`
- X-Frame-Options: `DENY`
- Referrer-Policy: `strict-origin-when-cross-origin`

Justification for `style-src 'unsafe-inline'`: Tailwind CSS generates utility classes at build time that are injected as inline styles. No user-supplied CSS is ever rendered.

## Pattern 5: Safe Markdown Rendering (Security)

Addresses: NFR-FE-04 (SECURITY-05), SECURITY-09

Agent messages contain markdown. Rendering pipeline:

```
Raw markdown (from agent)
  |
  v
react-markdown (parse to AST)
  |
  v
rehype-sanitize (strip dangerous HTML: script, iframe, event handlers)
  |
  v
Safe React elements (rendered to DOM)
```

- No `dangerouslySetInnerHTML` anywhere in codebase
- Allowed elements: p, strong, em, code, pre, ul, ol, li, table, thead, tbody, tr, th, td, h1-h6, a (with rel="noopener noreferrer")
- Blocked: script, iframe, object, embed, form, input, style

## Pattern 6: Code Splitting (Performance)

Addresses: NFR-FE-01 (< 500 KB bundle)

Vite route-level code splitting via React.lazy:

- Main bundle: App, ChatPanel, MessageInput, MessageList (always needed)
- Lazy-loaded: DataDetailView (loaded on first "View details" click)
- Shadcn/ui components: tree-shaken — only imported components included

Expected bundle breakdown:
- React + ReactDOM: ~45 KB gzipped
- Zustand: ~2 KB gzipped
- Shadcn/ui components (used subset): ~30-50 KB gzipped
- Tailwind CSS (purged): ~15-25 KB gzipped
- react-markdown + rehype: ~30 KB gzipped
- Application code: ~20-40 KB gzipped
- Total estimate: ~150-200 KB gzipped (well under 500 KB target)

## Pattern 7: Accessible Component Composition (Accessibility)

Addresses: NFR-FE-05, BR-FE-12

Shadcn/ui provides accessible primitives. Additional patterns:

- MessageList: `role="log"` container with `aria-live="polite"` — screen readers announce new messages without interrupting
- CapacityBar: Shadcn Progress component with `aria-valuenow`, `aria-valuemin="0"`, `aria-valuemax="100"`
- ApprovalCard: on mount, `useEffect` moves focus to first action button via `ref.current.focus()`
- All buttons: minimum 44x44px via Tailwind `min-h-11 min-w-11`
- Color + text: every colored indicator (green/yellow/red bars) also shows percentage text

## Pattern 8: Structured Console Logging (Observability)

Addresses: NFR-FE-07, SECURITY-03

Logging utility wrapping `console.*` with structured format:

```
[WebSocket] Connected to wss://api.example.com
[WebSocket] Disconnected — reconnecting (attempt 1)
[Store] Phase updated: impact_assessment -> capacity_analysis
[ErrorBoundary] ChatPanel crashed: TypeError at MessageContent.tsx:42
```

- Production: `console.error` and `console.warn` only (no `console.log`)
- Development: all levels enabled
- Controlled via `import.meta.env.MODE` check
- Never logs message content, user input, or PII (SECURITY-03)

## Security Compliance Summary

| Rule | Status | Implementation |
|------|--------|---------------|
| SECURITY-04 | Compliant | CloudFront response headers policy (Pattern 4) |
| SECURITY-05 | Compliant | Input validation (BR-FE-01) + rehype-sanitize (Pattern 5) |
| SECURITY-09 | Compliant | Source maps stripped, no console.log in prod, generic errors |
| SECURITY-10 | Compliant | pnpm-lock.yaml committed, exact versions, no CDN scripts |
| SECURITY-13 | Compliant | No external CDN scripts; all bundled locally |
| SECURITY-15 | Compliant | Error boundaries fail closed (Pattern 2), input disabled on disconnect |
| SECURITY-03 | Compliant | Structured logging, no PII in logs (Pattern 8) |
| SECURITY-01 | N/A | Frontend has no data persistence stores |
| SECURITY-02 | N/A | Frontend is not a network intermediary |
| SECURITY-06 | N/A | No IAM policies in frontend (handled by Infrastructure unit) |
| SECURITY-07 | N/A | No network configuration in frontend (handled by Infrastructure unit) |
| SECURITY-08 | N/A | No authentication for MVP; no server-side authorization in SPA |
| SECURITY-11 | Compliant | Security logic isolated in sanitization module; rate limiting N/A for single-user demo |
| SECURITY-12 | N/A | No authentication for MVP |
| SECURITY-14 | N/A | No server-side alerting in frontend; console logging covers client-side (Pattern 8) |
