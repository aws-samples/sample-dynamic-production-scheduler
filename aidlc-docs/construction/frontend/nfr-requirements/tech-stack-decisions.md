# Tech Stack Decisions — Unit 8: Frontend

## Core Framework

| Technology | Version | Rationale |
|-----------|---------|-----------|
| React | 18.x | Automatic batching for streaming token updates, concurrent features |
| TypeScript | 5.x | Strict mode, type safety across all components and store |
| Vite | 5.x | Fast HMR, optimized production builds, native ESM |

## UI Layer

| Technology | Version | Rationale |
|-----------|---------|-----------|
| Shadcn/ui | latest | Accessible component primitives, dark mode via CSS variables, copy-paste ownership |
| Tailwind CSS | 3.x | Utility-first styling, dark mode via `dark:` variants, small production CSS |
| Radix UI | (via Shadcn) | Headless accessible primitives underlying Shadcn components |
| Lucide React | latest | Icon library used by Shadcn/ui |

## State Management

| Technology | Version | Rationale |
|-----------|---------|-----------|
| Zustand | 4.x | Lightweight (< 2 KB), slice-based subscriptions for minimal re-renders during streaming |

## Markdown Rendering

| Technology | Version | Rationale |
|-----------|---------|-----------|
| react-markdown | 9.x | Safe markdown rendering for agent messages |
| rehype-sanitize | 6.x | HTML sanitization to prevent XSS (SECURITY-05) |

## WebSocket

| Technology | Version | Rationale |
|-----------|---------|-----------|
| Native WebSocket API | — | No library needed; reconnection logic is custom (< 50 lines) |

## Build & Dev

| Technology | Version | Rationale |
|-----------|---------|-----------|
| Vite | 5.x | Dev server with HMR, production bundling with Rollup |
| pnpm | 8.x | Fast, disk-efficient package manager, strict dependency resolution |
| PostCSS | (via Tailwind) | Tailwind CSS processing |

## Testing

| Technology | Version | Rationale |
|-----------|---------|-----------|
| Vitest | 1.x | Vite-native test runner, fast, ESM-first |
| @testing-library/react | 14.x | Component testing with user-centric queries |
| @testing-library/jest-dom | 6.x | Custom matchers for DOM assertions |
| jsdom | (via Vitest) | DOM environment for component tests |

## Code Quality

| Technology | Version | Rationale |
|-----------|---------|-----------|
| ESLint | 8.x | Linting with typescript-eslint and react-hooks plugins |
| Prettier | 3.x | Code formatting |
| TypeScript strict mode | — | No `any`, strict null checks, strict function types |

## Deployment

| Technology | Rationale |
|-----------|-----------|
| S3 + CloudFront | Static SPA hosting, HTTPS, security headers via CloudFront response headers policy |
| CloudFront Functions | Set CSP and security headers (SECURITY-04) |

## Decisions NOT Made (Deferred)

| Decision | Reason |
|---------|--------|
| Authentication library | No auth for MVP (NFR-04.2) |
| i18n framework | English only for MVP |
| Analytics/RUM | Console logging only for MVP |
| Service worker / PWA | Not needed for internal demo |
| CSS-in-JS (Emotion, styled-components) | Tailwind CSS chosen instead |
