import { create } from "zustand";
import { applyTransferToFacilityData } from "@/lib/dashboardData";
import type {
  ChatMessage,
  WorkflowPhase,
  ConnectionStatus,
  OrderDecisionRequest,
  StructuredPayload,
  CapacitySnapshot,
  AuditEntry,
  SidePanelMode,
  SubAgentInfo,
  OrderDecision,
  PlannerIdentity,
  AppView,
  DashboardView,
  Notification,
  TransferRequest,
  FacilityStatus,
  DisruptionSession,
  DisruptionPhase,
  DisruptionAgentStatus,
  ProductionOrder,
  DelayCandidate,
  FunnelOrder,
  KanbanColumn,
  PlantId,
  UiCapacityImpact,
  UiTransferOrder,
} from "@/types";
import { logger } from "@/lib/logger";

export interface AppState {
  // Session
  session: {
    sessionId: string | null;
    currentPhase: WorkflowPhase;
    activeAgent: string | null;
  };
  // Connection
  connection: {
    status: ConnectionStatus;
    reconnectAttempt: number;
  };
  // Chat
  chat: {
    messages: ChatMessage[];
    isAgentTyping: boolean;
  };
  // Side Panel
  sidePanel: {
    mode: SidePanelMode;
    pendingDecision: OrderDecisionRequest | null;
    detailData: StructuredPayload | null;
    previousMode: SidePanelMode | null;
  };
  // Capacity
  capacity: CapacitySnapshot | null;
  // Sub-agents
  subAgents: SubAgentInfo[];
  // Order decision history
  orderHistory: OrderDecision[];
  // Audit
  audit: { entries: AuditEntry[] };
  // Planner identity (Rework 4)
  planner: PlannerIdentity | null;
  // App view (Rework 4)
  currentView: AppView;
  dashboardView: DashboardView;
  // Notifications (Rework 4)
  notifications: Notification[];
  // Transfer requests (Rework 4)
  transferRequests: TransferRequest[];
  // Facility data (Rework 4)
  facilityData: FacilityStatus | null;
  // Disruption workflow (Rework 5)
  disruption: DisruptionSession | null;
}

export interface AppActions {
  setSessionId: (id: string) => void;
  setConnectionStatus: (status: ConnectionStatus) => void;
  incrementReconnect: () => void;
  resetReconnect: () => void;
  addUserMessage: (id: string, text: string) => void;
  appendStreamToken: (messageId: string, token: string, done: boolean) => void;
  attachStructuredData: (messageId: string, data: StructuredPayload) => void;
  setPhase: (phase: WorkflowPhase) => void;
  setActiveAgent: (agent: string | null) => void;
  updateCapacity: (snapshot: CapacitySnapshot) => void;
  setPendingDecision: (request: OrderDecisionRequest | null) => void;
  setSidePanelMode: (mode: SidePanelMode) => void;
  updateSubAgent: (info: SubAgentInfo) => void;
  addOrderDecision: (decision: OrderDecision) => void;
  showDetail: (data: StructuredPayload) => void;
  closeDetail: () => void;
  addAuditEntry: (entry: AuditEntry) => void;
  addErrorMessage: (text: string) => void;
  clearChat: () => void;
  // Rework 4 actions
  setPlanner: (planner: PlannerIdentity) => void;
  setCurrentView: (view: AppView) => void;
  setDashboardView: (view: DashboardView) => void;
  addNotification: (notification: Notification) => void;
  acknowledgeNotification: (id: string) => void;
  addTransferRequest: (request: TransferRequest) => void;
  setTransferRequests: (requests: TransferRequest[]) => void;
  updateTransferRequest: (id: string, updates: Partial<TransferRequest>) => void;
  setFacilityData: (data: FacilityStatus | null) => void;
  // Rework 5 disruption actions
  startDisruption: (plant: PlantId) => void;
  setDisruptionPhase: (phase: DisruptionPhase) => void;
  setDisruptionAgentStatus: (name: string, status: DisruptionAgentStatus["status"], summary?: string | null) => void;
  setDisruptionImpactResults: (orders: ProductionOrder[]) => void;
  setDisruptionCapacityResults: (snapshot: CapacitySnapshot) => void;
  setDisruptionDelayCandidates: (candidates: DelayCandidate[]) => void;
  addDisruptionDelayDecision: (orderId: string, decision: "approve" | "reject") => void;
  advanceDelayIndex: () => void;
  setDisruptionFunnelOrders: (orders: FunnelOrder[]) => void;
  addDisruptionFunnelDecision: (orderId: string, decision: KanbanColumn) => void;
  advanceFunnelIndex: () => void;
  setDisruptionSummary: (text: string) => void;
  clearDisruption: () => void;
  // Rework 7 actions
  setDisruptionCapacityImpact: (impact: UiCapacityImpact) => void;
  autoFlowTransferOrders: (orders: UiTransferOrder[]) => void;
  acceptTransfer: (transferId: string, reason?: string) => void;
  rejectTransfer: (transferId: string, reason?: string) => void;
}

const initialState: AppState = {
  session: { sessionId: null, currentPhase: "idle", activeAgent: null },
  connection: { status: "disconnected", reconnectAttempt: 0 },
  chat: { messages: [], isAgentTyping: false },
  sidePanel: {
    mode: "tracker",
    pendingDecision: null,
    detailData: null,
    previousMode: null,
  },
  capacity: null,
  subAgents: [],
  orderHistory: [],
  audit: { entries: [] },
  planner: null,
  currentView: "dashboard",
  dashboardView: "jobs",
  notifications: [],
  transferRequests: [],
  facilityData: null,
  disruption: null,
};

export const useStore = create<AppState & AppActions>()((set) => ({
  ...initialState,

  setSessionId: (id) =>
    set((s) => ({ session: { ...s.session, sessionId: id } })),

  setConnectionStatus: (status) =>
    set((s) => ({ connection: { ...s.connection, status } })),

  incrementReconnect: () =>
    set((s) => ({
      connection: {
        ...s.connection,
        reconnectAttempt: s.connection.reconnectAttempt + 1,
      },
    })),

  resetReconnect: () =>
    set((s) => ({ connection: { ...s.connection, reconnectAttempt: 0 } })),

  addUserMessage: (id, text) =>
    set((s) => ({
      chat: {
        ...s.chat,
        messages: [
          ...s.chat.messages,
          {
            id,
            role: "user",
            content: text,
            agentName: null,
            timestamp: new Date().toISOString(),
            isStreaming: false,
            structuredData: null,
            expandableReasoning: null,
            uiData: null,
            disruptionPhase: s.disruption?.phase ?? null,
          },
        ],
      },
    })),

  appendStreamToken: (messageId, token, done) =>
    set((s) => {
      const msgs = [...s.chat.messages];
      const idx = msgs.findIndex((m) => m.id === messageId);
      if (idx >= 0) {
        const msg = { ...msgs[idx]! };
        msg.content += token;
        if (done) msg.isStreaming = false;
        msgs[idx] = msg;
      } else {
        msgs.push({
          id: messageId,
          role: "assistant",
          content: token,
          agentName: s.session.activeAgent,
          timestamp: new Date().toISOString(),
          isStreaming: !done,
          structuredData: null,
          expandableReasoning: null,
          uiData: null,
          disruptionPhase: s.disruption?.phase ?? null,
        });
      }
      return { chat: { messages: msgs, isAgentTyping: !done } };
    }),

  attachStructuredData: (messageId, data) =>
    set((s) => {
      const msgs = s.chat.messages.map((m) =>
        m.id === messageId ? { ...m, structuredData: data } : m,
      );
      return { chat: { ...s.chat, messages: msgs } };
    }),

  setPhase: (phase) => {
    logger.info("Store", `Phase updated: ${phase}`);
    set((s) => ({ session: { ...s.session, currentPhase: phase } }));
  },

  setActiveAgent: (agent) => {
    logger.info("Store", `Active agent: ${agent ?? "none"}`);
    set((s) => ({ session: { ...s.session, activeAgent: agent } }));
  },

  updateCapacity: (snapshot) => set({ capacity: snapshot }),

  setPendingDecision: (request) =>
    set((s) => ({
      sidePanel: {
        ...s.sidePanel,
        mode: request ? "approval" : "tracker",
        pendingDecision: request,
      },
    })),

  setSidePanelMode: (mode) =>
    set((s) => ({
      sidePanel: { ...s.sidePanel, mode },
    })),

  updateSubAgent: (info) =>
    set((s) => {
      const agents = [...s.subAgents];
      const idx = agents.findIndex((a) => a.name === info.name);
      if (idx >= 0) {
        agents[idx] = info;
      } else {
        agents.push(info);
      }
      return { subAgents: agents };
    }),

  addOrderDecision: (decision) =>
    set((s) => ({
      orderHistory: [...s.orderHistory, decision],
    })),

  showDetail: (data) =>
    set((s) => ({
      sidePanel: {
        ...s.sidePanel,
        mode: "detail",
        detailData: data,
        previousMode: s.sidePanel.mode === "detail" ? s.sidePanel.previousMode : s.sidePanel.mode,
      },
    })),

  closeDetail: () =>
    set((s) => ({
      sidePanel: {
        ...s.sidePanel,
        mode: s.sidePanel.previousMode ?? "tracker",
        detailData: null,
        previousMode: null,
      },
    })),

  addAuditEntry: (entry) =>
    set((s) => ({
      audit: { entries: [...s.audit.entries.slice(-19), entry] },
    })),

  addErrorMessage: (text) =>
    set((s) => ({
      chat: {
        ...s.chat,
        messages: [
          ...s.chat.messages,
          {
            id: crypto.randomUUID(),
            role: "assistant",
            content: text,
            agentName: "System",
            timestamp: new Date().toISOString(),
            isStreaming: false,
            structuredData: null,
            expandableReasoning: null,
            uiData: null,
            disruptionPhase: s.disruption?.phase ?? null,
          },
        ],
      },
    })),

  clearChat: () =>
    set({ chat: { messages: [], isAgentTyping: false } }),

  // Rework 4 actions
  setPlanner: (planner) => set({ planner }),

  setCurrentView: (view) => set({ currentView: view }),

  setDashboardView: (view) => set({ dashboardView: view }),

  addNotification: (notification) =>
    set((s) => ({ notifications: [...s.notifications, notification] })),

  acknowledgeNotification: (id) =>
    set((s) => ({
      notifications: s.notifications.map((n) =>
        n.id === id ? { ...n, acknowledged: true } : n,
      ),
    })),

  addTransferRequest: (request) =>
    set((s) => ({ transferRequests: [...s.transferRequests, request] })),

  setTransferRequests: (requests) =>
    set(() => ({ transferRequests: requests })),

  updateTransferRequest: (id, updates) =>
    set((s) => ({
      transferRequests: s.transferRequests.map((r) =>
        r.id === id ? { ...r, ...updates } : r,
      ),
    })),

  setFacilityData: (data) => set({ facilityData: data }),

  // Rework 5 disruption actions
  startDisruption: (plant) =>
    set(() => ({
      disruption: {
        phase: "round1",
        plant,
        sessionId: null,
        agents: [
          { name: "Impact Assessment", status: "idle", summary: null },
          { name: "Capacity & Optimization", status: "idle", summary: null },
        ],
        impactResults: [],
        capacityResults: null,
        capacityImpact: null,
        delayCandidates: [],
        delayDecisions: {},
        currentDelayIndex: 0,
        funnelOrders: [],
        funnelDecisions: {},
        currentFunnelIndex: 0,
        totalFreedCapacity: "0",
        summaryText: null,
        phaseStartMsgCount: 0,
      },
      // Clear chat so disruption views start fresh
      chat: { messages: [], isAgentTyping: false },
      // Reset session so orchestrator starts fresh
      session: { sessionId: null, currentPhase: "idle", activeAgent: null },
    })),

  setDisruptionPhase: (phase) =>
    set((s) => s.disruption ? { disruption: { ...s.disruption, phase, phaseStartMsgCount: s.chat.messages.length } } : {}),

  setDisruptionAgentStatus: (name, status, summary) =>
    set((s) => {
      if (!s.disruption) return {};
      const agents = s.disruption.agents.map((a) =>
        a.name === name ? { ...a, status, summary: summary ?? a.summary } : a,
      );
      return { disruption: { ...s.disruption, agents } };
    }),

  setDisruptionImpactResults: (orders) =>
    set((s) => s.disruption ? { disruption: { ...s.disruption, impactResults: orders } } : {}),

  setDisruptionCapacityResults: (snapshot) =>
    set((s) => s.disruption ? { disruption: { ...s.disruption, capacityResults: snapshot } } : {}),

  setDisruptionDelayCandidates: (candidates) =>
    set((s) => s.disruption ? { disruption: { ...s.disruption, delayCandidates: candidates, currentDelayIndex: 0 } } : {}),

  addDisruptionDelayDecision: (orderId, decision) =>
    set((s) => {
      if (!s.disruption) return {};
      return {
        disruption: {
          ...s.disruption,
          delayDecisions: { ...s.disruption.delayDecisions, [orderId]: decision },
        },
      };
    }),

  advanceDelayIndex: () =>
    set((s) => {
      if (!s.disruption) return {};
      return { disruption: { ...s.disruption, currentDelayIndex: s.disruption.currentDelayIndex + 1 } };
    }),

  setDisruptionFunnelOrders: (orders) =>
    set((s) => {
      if (!s.disruption) return {};
      const funnelDecisions: Record<string, KanbanColumn> = {};
      orders.forEach((o) => { funnelDecisions[o.orderId] = "pending"; });
      return { disruption: { ...s.disruption, funnelOrders: orders, funnelDecisions, currentFunnelIndex: 0 } };
    }),

  addDisruptionFunnelDecision: (orderId, decision) =>
    set((s) => {
      if (!s.disruption) return {};
      return {
        disruption: {
          ...s.disruption,
          funnelDecisions: { ...s.disruption.funnelDecisions, [orderId]: decision },
        },
      };
    }),

  advanceFunnelIndex: () =>
    set((s) => {
      if (!s.disruption) return {};
      return { disruption: { ...s.disruption, currentFunnelIndex: s.disruption.currentFunnelIndex + 1 } };
    }),

  setDisruptionSummary: (text) =>
    set((s) => s.disruption ? { disruption: { ...s.disruption, summaryText: text } } : {}),

  clearDisruption: () => set({ disruption: null }),

  // Rework 7 actions
  setDisruptionCapacityImpact: (impact) =>
    set((s) => s.disruption ? { disruption: { ...s.disruption, capacityImpact: impact } } : {}),

  autoFlowTransferOrders: (orders) =>
    set((s) => {
      const sourcePlant = (s.disruption?.plant ?? "Florida") as PlantId;
      const targetPlant = sourcePlant === "Florida" ? "Ohio" : "Florida";
      const newTransfers = orders.map((o) => ({
        id: crypto.randomUUID(),
        orderId: o.orderId,
        order: {
          orderId: o.orderId,
          plant: sourcePlant as "Florida" | "Ohio",
          productFamily: o.product,
          quantity: 0,
          dueDate: o.dueDate,
          customerName: o.customer,
          customerTier: (o.customerTier || "Tier1") as "Tier1" | "Tier2" | "Tier3",
          orderValue: parseFloat(o.value.replace(/[^0-9.]/g, "")) || 0,
          priority: (o.priority || null) as "P1" | "P2" | "P3" | null,
          status: "Active",
          transferredFrom: null,
        },
        recommendation: o.recommendation,
        reasoning: o.reasoning,
        funnelResults: o.funnelResults.map((f) => ({
          layer: f.layer as 1 | 2 | 3 | 4,
          name: f.name as "Equipment" | "Material" | "Utilization" | "Cascade",
          passed: f.passed,
          detail: f.detail,
        })),
        status: "submitted_for_review" as const,
        proposedAt: new Date().toISOString(),
      }));
      // Fire-and-forget: persist to DynamoDB
      import("@/lib/transferApi").then((api) =>
        api.submitTransfers(orders, sourcePlant, targetPlant).catch(() => {}),
      );
      return { transferRequests: [...s.transferRequests, ...newTransfers] };
    }),

  acceptTransfer: (transferId, reason) =>
    set((s) => {
      const transfers = s.transferRequests.map((t) =>
        t.id === transferId
          ? { ...t, status: "approved" as const, decidedAt: new Date().toISOString() }
          : t,
      );
      // Add notification
      const transfer = s.transferRequests.find((t) => t.id === transferId);
      const newNotifications = transfer
        ? [
            ...s.notifications,
            {
              id: crypto.randomUUID(),
              type: "transfer_approved" as const,
              title: "Transfer Accepted",
              message: `Order ${transfer.orderId} transfer accepted${reason ? `: ${reason}` : ""}`,
              timestamp: new Date().toISOString(),
              acknowledged: false,
              plant: transfer.order.plant,
            },
          ]
        : s.notifications;
      // Update facility data to reflect the transfer on the dashboard
      let updatedFacility = s.facilityData;
      if (transfer && updatedFacility) {
        const receiverPlant = (transfer.order.plant === "Florida" ? "Ohio" : "Florida") as import("@/types").PlantId;
        updatedFacility = applyTransferToFacilityData(updatedFacility, transfer, receiverPlant);
      }
      return { transferRequests: transfers, notifications: newNotifications, facilityData: updatedFacility };
    }),

  rejectTransfer: (transferId, reason) =>
    set((s) => {
      const transfers = s.transferRequests.map((t) =>
        t.id === transferId
          ? { ...t, status: "declined" as const, declineReason: reason, decidedAt: new Date().toISOString() }
          : t,
      );
      const transfer = s.transferRequests.find((t) => t.id === transferId);
      const newNotifications = transfer
        ? [
            ...s.notifications,
            {
              id: crypto.randomUUID(),
              type: "transfer_declined" as const,
              title: "Transfer Declined",
              message: `Order ${transfer.orderId} transfer declined${reason ? `: ${reason}` : ""}`,
              timestamp: new Date().toISOString(),
              acknowledged: false,
              plant: transfer.order.plant,
            },
          ]
        : s.notifications;
      return { transferRequests: transfers, notifications: newNotifications };
    }),
}));
