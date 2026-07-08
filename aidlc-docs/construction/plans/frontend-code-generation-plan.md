# Code Generation Plan — Unit 8: Frontend

## Context
- **Unit**: Frontend SPA (React 18 + TypeScript + Vite 5)
- **Location**: `frontend-spa/` in workspace root
- **Stack**: Shadcn/ui, Tailwind CSS, Zustand, react-markdown, rehype-sanitize
- **Testing**: Vitest + React Testing Library
- **Package Manager**: pnpm

## Code Generation Steps

- [x] Step 1: Project scaffolding (Vite + pnpm + TypeScript + Tailwind + Shadcn/ui config)
- [x] Step 2: TypeScript types (`src/types/`) — domain entities from functional design
- [x] Step 3: Zustand store (`src/store/`) — app store with all slices and actions
- [x] Step 4: WebSocket client (`src/lib/websocket.ts`) — connection, reconnect, dispatch
- [x] Step 5: Logging utility (`src/lib/logger.ts`) — structured console logging
- [x] Step 6: Markdown sanitizer (`src/lib/markdown.tsx`) — react-markdown + rehype-sanitize
- [x] Step 7: UI components — App, AppHeader, MainLayout, ConnectionIndicator
- [x] Step 8: Chat components — ChatPanel, MessageList, ChatMessage, AgentBadge, MessageInput
- [x] Step 9: Chat sub-components — StructuredDataSummary, ViewDetailsButton, ExpandableReasoning
- [x] Step 10: Side panel components — SidePanel, PhaseProgressBar, PanelContent
- [x] Step 11: Side panel content — CapacityTracker, CapacityBar, ApprovalCard, DataDetailView
- [x] Step 12: Audit trail — AuditTrailSection, AuditEntry
- [x] Step 13: Error boundaries — AppErrorBoundary, ChatPanelBoundary, SidePanelBoundary
- [x] Step 14: Unit tests — store, WebSocket, components (Vitest + RTL)
- [x] Step 15: README and code generation summary
