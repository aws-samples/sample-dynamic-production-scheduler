# NFR Requirements Plan — Unit 8: Frontend

## Context
- **Unit**: Frontend SPA (React + TypeScript + Vite)
- **UI Library**: Shadcn/ui + Tailwind CSS
- **State Management**: Zustand
- **Communication**: WebSocket (bidirectional streaming)
- **Dark Mode**: System preference auto-detect

## Plan Steps

- [x] Step 1: Collect user answers to NFR questions below
- [x] Step 2: Analyze answers for ambiguities (Q2: user asked for recommendation — factory plants use Chrome/Edge on Windows; mapped to A: modern evergreen)
- [x] Step 3: Generate `aidlc-docs/construction/frontend/nfr-requirements/nfr-requirements.md`
- [x] Step 4: Generate `aidlc-docs/construction/frontend/nfr-requirements/tech-stack-decisions.md`
- [x] Step 5: Update aidlc-state.md and audit.md

---

## Questions

## Question 1: Bundle Size Target
What is the acceptable initial JavaScript bundle size for the SPA?

A) < 200 KB gzipped (aggressive — requires heavy code splitting)
B) < 500 KB gzipped (balanced — standard code splitting with lazy routes)
C) < 1 MB gzipped (relaxed — acceptable for internal/demo tool)
D) No specific target — optimize where easy but don't over-invest for MVP
X) Other (please describe after [Answer]: tag below)

[Answer]: B

## Question 2: Browser Support
Which browsers must be supported?

A) Modern evergreen only (Chrome, Firefox, Safari, Edge — latest 2 versions)
B) Modern evergreen + Safari iOS 15+
C) Include IE11 / legacy browser support
X) Other (please describe after [Answer]: tag below)

[Answer]: What browsers are usually used on the factory plant

## Question 3: Initial Page Load Time Target
What is the acceptable time from navigation to interactive UI?

A) < 2 seconds on broadband (aggressive)
B) < 3 seconds on broadband (standard)
C) < 5 seconds on broadband (relaxed — acceptable for internal demo)
X) Other (please describe after [Answer]: tag below)

[Answer]: C

## Question 4: Streaming Token Render Latency
The requirements specify < 100ms token render latency (NFR-01.4). Is this target correct?

A) Yes — < 100ms from WebSocket receipt to DOM update
B) Relax to < 200ms — sufficient for readable streaming
C) Tighter — < 50ms for truly fluid streaming
X) Other (please describe after [Answer]: tag below)

[Answer]: B

## Question 5: Testing Strategy
What testing approach for the frontend?

A) Unit tests only (Vitest + React Testing Library)
B) Unit tests + integration tests (Vitest + RTL + MSW for WebSocket mocking)
C) Unit + integration + E2E (add Playwright for critical user flows)
D) Minimal — a few smoke tests, rely on manual QA for MVP
X) Other (please describe after [Answer]: tag below)

[Answer]: A

## Question 6: Error Monitoring & Observability
How should frontend errors be tracked in production?

A) Console logging only (simplest for MVP/demo)
B) Structured logging to CloudWatch via API endpoint
C) Third-party error tracking (Sentry, Datadog RUM, etc.)
D) No preference — recommend what fits the AWS stack
X) Other (please describe after [Answer]: tag below)

[Answer]: A

## Question 7: Accessibility Compliance Target
What level of accessibility compliance should the frontend target?

A) WCAG 2.1 AA — full compliance (keyboard nav, screen reader, contrast ratios, ARIA)
B) Best-effort accessibility — keyboard nav + ARIA labels on key elements (as defined in BR-FE-12)
C) Minimal — data-testid for automation, basic keyboard support
X) Other (please describe after [Answer]: tag below)

[Answer]: B

## Question 8: Offline / Degraded Mode Behavior
When WebSocket is disconnected, what should the UI do beyond the reconnection logic in BR-FE-08?

A) Show read-only chat history + "Reconnecting..." banner (current design)
B) Queue user messages locally and send on reconnect
C) Show a full-screen "Connection Lost" overlay blocking interaction
X) Other (please describe after [Answer]: tag below)

[Answer]: A
