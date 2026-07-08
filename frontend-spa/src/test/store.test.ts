import { describe, it, expect, beforeEach } from "vitest";
import { useStore } from "@/store";

function reset() {
  useStore.setState({
    session: { sessionId: null, currentPhase: "idle", activeAgent: null },
    connection: { status: "connecting", reconnectAttempt: 0 },
    chat: { messages: [], isAgentTyping: false },
    sidePanel: { mode: "tracker", pendingDecision: null, detailData: null, previousMode: null },
    capacity: null,
    audit: { entries: [] },
  });
}

describe("useStore", () => {
  beforeEach(reset);

  it("sets session id", () => {
    useStore.getState().setSessionId("abc");
    expect(useStore.getState().session.sessionId).toBe("abc");
  });

  it("sets connection status", () => {
    useStore.getState().setConnectionStatus("connected");
    expect(useStore.getState().connection.status).toBe("connected");
  });

  it("increments and resets reconnect", () => {
    useStore.getState().incrementReconnect();
    useStore.getState().incrementReconnect();
    expect(useStore.getState().connection.reconnectAttempt).toBe(2);
    useStore.getState().resetReconnect();
    expect(useStore.getState().connection.reconnectAttempt).toBe(0);
  });

  it("adds user message", () => {
    useStore.getState().addUserMessage("m1", "hello");
    const msgs = useStore.getState().chat.messages;
    expect(msgs).toHaveLength(1);
    expect(msgs[0]!.role).toBe("user");
    expect(msgs[0]!.content).toBe("hello");
  });

  it("appends stream token to new message", () => {
    useStore.getState().appendStreamToken("m2", "Hi", false);
    const msgs = useStore.getState().chat.messages;
    expect(msgs).toHaveLength(1);
    expect(msgs[0]!.content).toBe("Hi");
    expect(msgs[0]!.isStreaming).toBe(true);
    expect(useStore.getState().chat.isAgentTyping).toBe(true);
  });

  it("appends stream token to existing message", () => {
    useStore.getState().appendStreamToken("m3", "He", false);
    useStore.getState().appendStreamToken("m3", "llo", true);
    const msgs = useStore.getState().chat.messages;
    expect(msgs).toHaveLength(1);
    expect(msgs[0]!.content).toBe("Hello");
    expect(msgs[0]!.isStreaming).toBe(false);
    expect(useStore.getState().chat.isAgentTyping).toBe(false);
  });

  it("attaches structured data", () => {
    useStore.getState().addUserMessage("m4", "test");
    useStore.getState().attachStructuredData("m4", {
      type: "order_table",
      title: "Orders",
      data: { count: 5 },
    });
    expect(useStore.getState().chat.messages[0]!.structuredData?.title).toBe("Orders");
  });

  it("sets phase", () => {
    useStore.getState().setPhase("impact_assessment");
    expect(useStore.getState().session.currentPhase).toBe("impact_assessment");
  });

  it("sets active agent", () => {
    useStore.getState().setActiveAgent("Impact Assessment Agent");
    expect(useStore.getState().session.activeAgent).toBe("Impact Assessment Agent");
  });

  it("updates capacity", () => {
    const snapshot = {
      rollingMill: { label: "Rolling Mill", used: 70, available: 100, unit: "hrs", thresholdPct: 90 },
      finishingLine: { label: "Finishing", used: 50, available: 100, unit: "hrs", thresholdPct: 90 },
      materialTons: { label: "Material", used: 80, available: 100, unit: "tons", thresholdPct: 90 },
      operatorHours: { label: "Operators", used: 40, available: 100, unit: "hrs", thresholdPct: 90 },
      bottleneck: "Material",
      lastUpdated: new Date().toISOString(),
    };
    useStore.getState().updateCapacity(snapshot);
    expect(useStore.getState().capacity?.bottleneck).toBe("Material");
  });

  it("manages pending decision and panel mode", () => {
    const req = {
      orderId: "PO-001",
      order: {
        orderId: "PO-001", plant: "Florida" as const, productFamily: "Steel",
        quantity: 100, dueDate: "2026-04-01", customerName: "Acme",
        customerTier: "Tier1" as const, orderValue: 50000, priority: "P1" as const, status: "active",
      },
      recommendation: "transfer" as const,
      funnelResults: [],
      reasoning: "test",
    };
    useStore.getState().setPendingDecision(req);
    expect(useStore.getState().sidePanel.mode).toBe("approval");
    useStore.getState().setPendingDecision(null);
    expect(useStore.getState().sidePanel.mode).toBe("tracker");
  });

  it("shows and closes detail view", () => {
    const data = { type: "order_table" as const, title: "T", data: {} };
    useStore.getState().showDetail(data);
    expect(useStore.getState().sidePanel.mode).toBe("detail");
    expect(useStore.getState().sidePanel.previousMode).toBe("tracker");
    useStore.getState().closeDetail();
    expect(useStore.getState().sidePanel.mode).toBe("tracker");
    expect(useStore.getState().sidePanel.detailData).toBeNull();
  });

  it("adds audit entry with max 20 cap", () => {
    for (let i = 0; i < 25; i++) {
      useStore.getState().addAuditEntry({
        id: `a${i}`, timestamp: new Date().toISOString(),
        agent: "Test", action: `action-${i}`, details: "", sessionId: "s1",
      });
    }
    expect(useStore.getState().audit.entries).toHaveLength(20);
  });

  it("adds error message", () => {
    useStore.getState().addErrorMessage("Something broke");
    const msgs = useStore.getState().chat.messages;
    expect(msgs).toHaveLength(1);
    expect(msgs[0]!.agentName).toBe("System");
    expect(msgs[0]!.content).toBe("Something broke");
  });
});
