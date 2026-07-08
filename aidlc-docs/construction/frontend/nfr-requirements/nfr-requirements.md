# NFR Requirements — Unit 8: Frontend

## NFR-FE-01: Performance

### Bundle Size
- Initial JS bundle: < 500 KB gzipped
- Code splitting: route-level lazy loading for side panel detail views
- Tree-shaking enabled via Vite production build

### Page Load
- Time to interactive: < 5 seconds on broadband
- Largest Contentful Paint (LCP): < 4 seconds
- First Input Delay (FID): < 100ms

### Streaming Latency
- WebSocket token receipt to DOM update: < 200ms
- React state update batching: use `unstable_batchedUpdates` or React 18 automatic batching
- Avoid re-rendering entire message list on each token — subscribe to individual message slices

### Rendering
- Message list virtualization not required for MVP (expect < 200 messages per session)
- Capacity tracker bar updates: CSS transition only (no JS animation library)

## NFR-FE-02: Browser Support

- Chrome (latest 2 versions)
- Edge (latest 2 versions)
- Firefox (latest 2 versions)
- Safari (latest 2 versions)

Rationale: Factory plant workstations typically run Chrome or Edge on Windows. Modern evergreen browsers cover this use case. No IE11 or legacy support needed.

## NFR-FE-03: Reliability

### WebSocket Reconnection
- Auto-reconnect with exponential backoff: 1s, 2s, 4s, 8s, 16s, 30s cap
- Unlimited retry attempts
- Session ID preserved across reconnections
- No message replay (MVP)

### Degraded Mode
- Read-only chat history visible during disconnection
- "Reconnecting..." banner in header (non-blocking)
- Input field disabled until reconnected
- No local message queuing (MVP)

### Error Boundaries
- React Error Boundary at App level catches render crashes
- Per-panel error boundaries (ChatPanel, SidePanel) for isolated recovery
- Fallback UI: "Something went wrong" with retry button

## NFR-FE-04: Security

### SECURITY-04: HTTP Security Headers
- Content-Security-Policy: `default-src 'self'; connect-src 'self' wss://*.amazonaws.com; style-src 'self' 'unsafe-inline'` (Tailwind requires unsafe-inline for utility classes)
- Strict-Transport-Security: `max-age=31536000; includeSubDomains`
- X-Content-Type-Options: `nosniff`
- X-Frame-Options: `DENY`
- Referrer-Policy: `strict-origin-when-cross-origin`
- CSP `unsafe-inline` for style-src justified: Tailwind CSS injects utility styles at build time; no user-supplied styles

### SECURITY-05: Input Validation
- Message input: max 2000 chars, trimmed, HTML entities escaped before send
- No raw HTML rendering — markdown rendered via safe parser (e.g., react-markdown with rehype-sanitize)
- WebSocket messages validated against expected ServerMessage schema before dispatch

### SECURITY-09: Hardening
- Production builds strip source maps
- No console.log in production (lint rule)
- Error messages never expose internal details (BR-FE-09)
- Vite env variables: only `VITE_` prefixed vars exposed to client

### SECURITY-10: Supply Chain
- Lock file (pnpm-lock.yaml) committed to version control
- Exact dependency versions in package.json
- No `latest` tags

### SECURITY-13: Integrity
- External CDN scripts (if any) must use SRI hashes
- MVP: all dependencies bundled locally, no external CDN scripts

## NFR-FE-05: Accessibility

- Best-effort WCAG 2.1 AA compliance
- Keyboard navigation: all interactive elements reachable via Tab
- ARIA labels on approval buttons with order ID context
- Chat message list: `role="log"`, `aria-live="polite"`
- Capacity bars: `aria-valuenow`, `aria-valuemin`, `aria-valuemax`
- Color never sole indicator — always paired with text/icon
- Focus management: approval card auto-focuses first action button
- Minimum touch target: 44x44px for buttons
- Contrast ratios: Shadcn/ui defaults meet AA for both light and dark themes

## NFR-FE-06: Testing

- Unit tests: Vitest + React Testing Library
- Coverage target: 70% line coverage for business logic (store actions, WebSocket dispatch, message assembly)
- Component tests: render + interaction tests for ChatMessage, ApprovalCard, CapacityTracker, MessageInput
- No integration or E2E tests for MVP
- Mock WebSocket via custom test utility (not MSW)

## NFR-FE-07: Observability

- Console logging only for MVP
- Structured console output: `[component] action detail` format
- WebSocket connection state changes logged
- Error boundary catches logged with component stack
- No remote error tracking for MVP

## NFR-FE-08: Maintainability

- TypeScript strict mode enabled
- ESLint + Prettier enforced
- Component files: one component per file
- Zustand store: single store with named slices (not multiple stores)
- All props typed via TypeScript interfaces (no `any`)
