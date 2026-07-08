import { describe, it, expect, beforeEach } from "vitest";
import { render, screen } from "@testing-library/react";
import { useStore } from "@/store";
import { ConnectionIndicator } from "@/components/ConnectionIndicator";
import { AppHeader } from "@/components/AppHeader";
import { AgentBadge } from "@/components/chat/AgentBadge";

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

describe("ConnectionIndicator", () => {
  beforeEach(reset);

  it("shows connecting when status is connecting", () => {
    render(<ConnectionIndicator />);
    expect(screen.getByText("Connecting...")).toBeTruthy();
  });

  it("shows reconnecting when status is reconnecting", () => {
    useStore.setState({ connection: { status: "reconnecting", reconnectAttempt: 1 } });
    render(<ConnectionIndicator />);
    expect(screen.getByText("Reconnecting...")).toBeTruthy();
  });

  it("renders nothing when connected", () => {
    useStore.setState({ connection: { status: "connected", reconnectAttempt: 0 } });
    const { container } = render(<ConnectionIndicator />);
    expect(container.innerHTML).toBe("");
  });
});

describe("AppHeader", () => {
  beforeEach(reset);

  it("renders title", () => {
    render(<AppHeader />);
    expect(screen.getByText("DisruptionAI")).toBeTruthy();
  });
});

describe("AgentBadge", () => {
  it("renders agent name", () => {
    render(<AgentBadge agentName="Impact Assessment Agent" />);
    expect(screen.getByText("Impact Assessment Agent")).toBeTruthy();
  });

  it("renders small variant", () => {
    const { container } = render(<AgentBadge agentName="System" small />);
    expect(container.querySelector("span")?.className).toContain("text-[10px]");
  });
});
