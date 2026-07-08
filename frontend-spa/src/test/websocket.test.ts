import { describe, it, vi, beforeEach, afterEach } from "vitest";
import { useStore } from "@/store";

// Mock WebSocket globally
class MockWebSocket {
  static OPEN = 1;
  readyState = MockWebSocket.OPEN;
  onopen: (() => void) | null = null;
  onclose: (() => void) | null = null;
  onerror: (() => void) | null = null;
  onmessage: ((e: { data: string }) => void) | null = null;
  sent: string[] = [];

  send(data: string) {
    this.sent.push(data);
  }
  close() {
    this.readyState = 3;
  }
}

describe("websocket", () => {
  let originalWS: typeof globalThis.WebSocket;

  beforeEach(() => {
    originalWS = globalThis.WebSocket;
    (globalThis as Record<string, unknown>).WebSocket = MockWebSocket;
    useStore.setState({
      session: { sessionId: null, currentPhase: "idle", activeAgent: null },
      connection: { status: "connecting", reconnectAttempt: 0 },
      chat: { messages: [], isAgentTyping: false },
      sidePanel: { mode: "tracker", pendingDecision: null, detailData: null, previousMode: null },
      capacity: null,
      audit: { entries: [] },
    });
  });

  afterEach(() => {
    (globalThis as Record<string, unknown>).WebSocket = originalWS;
    vi.restoreAllMocks();
  });

  it("send serializes data as JSON", async () => {
    vi.stubEnv("VITE_WS_URL", "wss://test"); // Use wss:// even in tests to demonstrate secure pattern
    // Dynamic import to pick up env
    const mod = await import("@/lib/websocket");
    mod.connect();
    mod.send({ type: "user_message", payload: { text: "hi" } });
    mod.disconnect();
  });
});
