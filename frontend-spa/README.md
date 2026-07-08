# DisruptionAI Frontend

> **⚠️ Note:** This is a demo/sample component, not intended for production use without security review.

React 18 SPA for the DisruptionAI production scheduling system.

## Tech Stack

- React 18 + TypeScript 5.7
- Vite 5 (build + dev server)
- Tailwind CSS 3.4 + Shadcn/ui primitives
- Zustand 4.5 (state management)
- react-markdown + rehype-sanitize (safe markdown rendering)
- Vitest + React Testing Library (testing)

## Getting Started

```bash
# Install dependencies
npm install

# Start dev server
npm run dev

# Run tests
npm test

# Type check
npx tsc --noEmit

# Production build
npm run build
```

## Environment Variables

This app reads deployment-specific configuration from a `.env` file (or runtime
`/config.json`). The `.env` file is **git-ignored** — do not commit it. Copy the
template and fill in values from your CDK stack outputs:

```bash
cp .env.example .env
# then edit .env with your deployment-specific values
```

Required variables (see `.env.example`):

```
VITE_API_URL=            # REST proxy Lambda Function URL (CDK output RestProxyUrl)
VITE_USER_POOL_ID=       # Cognito User Pool ID
VITE_USER_CLIENT_ID=     # Cognito User Pool App Client ID
VITE_IDENTITY_POOL_ID=   # Cognito Identity Pool ID
VITE_AWS_REGION=us-east-1
```

These are public client-side identifiers rather than authentication secrets, but
they are kept out of source control to avoid exposing account-specific
infrastructure details.

## Project Structure

```
src/
  components/
    chat/         # ChatPanel, MessageList, ChatMessage, AgentBadge, MessageInput
    side/         # SidePanel, CapacityTracker, ApprovalCard, DataDetailView, AuditTrail
    errors/       # Error boundaries (App, ChatPanel, SidePanel)
  lib/
    logger.ts     # Structured console logging
    markdown.tsx  # Safe markdown renderer
    websocket.ts  # WebSocket client with reconnection
  store/
    index.ts      # Zustand store (session, chat, capacity, audit)
  types/
    index.ts      # All TypeScript interfaces
  test/           # Unit tests
```
