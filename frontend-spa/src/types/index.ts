// --- Core Message Types ---

export interface ChatMessage {
  id: string;
  role: "user" | "assistant";
  content: string;
  agentName: string | null;
  timestamp: string;
  isStreaming: boolean;
  structuredData: StructuredPayload | null;
  expandableReasoning: string | null;
  /** Structured UI data from orchestrator's update_ui tool */
  uiData: UiPayload | null;
  /** Disruption phase this message belongs to — set when the message is created */
  disruptionPhase: string | null;
}

export interface StreamToken {
  messageId: string;
  token: string;
  done: boolean;
}

export type StructuredPayloadType =
  | "order_table"
  | "capacity_summary"
  | "delay_candidates"
  | "funnel_result"
  | "audit_trail";

export interface StructuredPayload {
  type: StructuredPayloadType;
  title: string;
  data: Record<string, unknown>;
}

// --- Order & Priority Types ---

export interface ProductionOrder {
  orderId: string;
  plant: "Florida" | "Ohio";
  productFamily: string;
  quantity: number;
  dueDate: string;
  customerName: string;
  customerTier: "Tier1" | "Tier2" | "Tier3";
  orderValue: number;
  priority: "P1" | "P2" | "P3" | null;
  status: string;
  transferredFrom?: PlantId | null;
}

export interface OrderDecisionRequest {
  orderId: string;
  order: ProductionOrder;
  recommendation:
    | "transfer"
    | "transfer_with_procurement"
    | "transfer_overtime"
    | "non_transferable";
  funnelResults: FunnelLayerResult[];
  reasoning: string;
}

export interface FunnelLayerResult {
  layer: 1 | 2 | 3 | 4;
  name: "Equipment" | "Material" | "Utilization" | "Cascade";
  passed: boolean;
  detail: string;
}

export interface OrderDecisionResponse {
  orderId: string;
  decision: "approve" | "skip" | "reject";
  reason: string | null;
}

// --- Capacity Tracker Types ---

export interface CapacitySnapshot {
  rollingMill: CapacityDimension;
  finishingLine: CapacityDimension;
  materialTons: CapacityDimension;
  operatorHours: CapacityDimension;
  bottleneck: string;
  lastUpdated: string;
}

export interface CapacityDimension {
  label: string;
  used: number;
  available: number;
  unit: string;
  thresholdPct: number;
}

// --- Session & Connection Types ---

export type WorkflowPhase =
  | "idle"
  | "disruption_intake"
  | "impact_assessment"
  | "capacity_analysis"
  | "delay_optimization"
  | "constraint_matching"
  | "what_if"
  | "summary"
  | "complete";

export type ConnectionStatus =
  | "connecting"
  | "connected"
  | "reconnecting"
  | "disconnected";

// --- Audit Types ---

export interface AuditEntry {
  id: string;
  timestamp: string;
  agent: string;
  action: string;
  details: string;
  sessionId: string;
}

// --- WebSocket Message Types ---

export type ClientMessageType =
  | "user_message"
  | "order_decision"
  | "constraint_input";

export interface ClientMessage {
  type: ClientMessageType;
  sessionId: string;
  payload: Record<string, unknown>;
}

export type ServerMessageType =
  | "stream_token"
  | "structured_data"
  | "order_decision_request"
  | "phase_update"
  | "capacity_update"
  | "agent_switch"
  | "error";

export interface ServerMessage {
  type: ServerMessageType;
  sessionId: string;
  payload: Record<string, unknown>;
}

// --- Side Panel Types ---

export type SidePanelMode = "tracker" | "approval" | "detail" | "agents" | "orders" | "visualizations";

// --- Sub-Agent Status Types ---

export interface SubAgentInfo {
  name: string;
  status: "idle" | "running" | "complete" | "error";
  startedAt: string | null;
  completedAt: string | null;
  summary: string | null;
}

// --- Order Decision History ---

export interface OrderDecision {
  orderId: string;
  decision: "approve" | "reject" | "skip";
  agentName: string;
  timestamp: string;
  reasoning: string | null;
}

// --- Visualization Data Types ---

export interface CascadeImpactData {
  orderId: string;
  layers: { name: string; passed: boolean; detail: string }[];
  recommendation: string;
}

export interface ScorecardData {
  orderId: string;
  scores: { criterion: string; weight: number; score: number; weighted: number }[];
  totalScore: number;
  priority: string;
}

export interface TransferFlowData {
  source: string;
  target: string;
  orders: { orderId: string; status: string; value: number }[];
}

// --- Planner Identity Types (Rework 4) ---

export type PlantId = "Florida" | "Ohio";
export type PlantDisplayName = "Miami" | "Ohio";

export interface PlannerIdentity {
  plant: PlantId;
  displayName: PlantDisplayName;
}

export const PLANT_DISPLAY_NAMES: Record<PlantId, PlantDisplayName> = {
  Florida: "Miami",
  Ohio: "Ohio",
};

// --- Dashboard Types (Rework 4) ---

export type AppView = "dashboard" | "chat" | "transfers" | "disruption" | "transfer-dashboard";
export type DashboardView = "jobs" | "efficiency";

export interface Notification {
  id: string;
  type: "disruption" | "transfer_declined" | "transfer_approved" | "transfer_request";
  title: string;
  message: string;
  timestamp: string;
  acknowledged: boolean;
  plant: PlantId;
}

export type TransferStatus =
  | "proposed"
  | "confirmed"
  | "pending_approval"
  | "approved"
  | "declined"
  | "resubmitted"
  | "submitted_for_review";

export interface TransferRequest {
  id: string;
  orderId: string;
  order: ProductionOrder;
  recommendation: string;
  reasoning: string;
  funnelResults: FunnelLayerResult[];
  status: TransferStatus;
  declineReason?: string;
  modifiedFields?: Record<string, unknown>;
  proposedAt: string;
  decidedAt?: string;
}

// --- Facility Status Types (Rework 4) ---

export interface MachineStatus {
  machineType: string;
  plant: PlantId;
  normalUtilizationPct: number;
  overtimeAvailablePct: number;
  weekendAvailablePct: number;
  status: "online" | "maintenance" | "offline";
}

export interface WorkforceStatus {
  plant: PlantId;
  totalOperators: number;
  allocated: number;
  surplus: number;
}

export interface MaterialLevel {
  materialType: string;
  plant: PlantId;
  currentTons: number;
  committedTons: number;
  surplusTons: number;
}

export interface FacilityStatus {
  plant: PlantId;
  machines: MachineStatus[];
  workforce: WorkforceStatus;
  materials: MaterialLevel[];
  orders: ProductionOrder[];
}

// --- Disruption Workflow Types (Rework 5) ---

export type DisruptionPhase =
  | "landing"
  | "round1"
  | "delay_optimization"
  | "constraint_funnel"
  | "capacity_summary"
  | "complete";

export type KanbanColumn = "pending" | "approved" | "rejected" | "skipped";

export interface DelayCandidate {
  orderId: string;
  order: ProductionOrder;
  freedCapacity: string;
  impactSummary: string;
}

export interface FunnelOrder {
  orderId: string;
  order: ProductionOrder;
  funnelResults: FunnelLayerResult[];
  recommendation: string;
  reasoning: string;
}

export interface DisruptionAgentStatus {
  name: string;
  status: "idle" | "running" | "complete" | "error";
  summary: string | null;
}

export interface DisruptionSession {
  phase: DisruptionPhase;
  plant: PlantId;
  sessionId: string | null;
  agents: DisruptionAgentStatus[];
  impactResults: ProductionOrder[];
  capacityResults: CapacitySnapshot | null;
  capacityImpact: UiCapacityImpact | null;
  delayCandidates: DelayCandidate[];
  delayDecisions: Record<string, "approve" | "reject">;
  currentDelayIndex: number;
  funnelOrders: FunnelOrder[];
  funnelDecisions: Record<string, KanbanColumn>;
  currentFunnelIndex: number;
  totalFreedCapacity: string;
  summaryText: string | null;
  /** Chat message count when the current phase started — used to filter phase-specific messages */
  phaseStartMsgCount: number;
}

// --- UI Payload Types (Rework 6) ---

export interface UiAgentStatus {
  name: string;
  status: "idle" | "running" | "complete" | "error";
  summary?: string | null;
}

export interface UiOrder {
  orderId: string;
  product?: string;
  customer?: string;
  customerTier?: string;
  value?: string;
  dueDate?: string;
  priority?: string;
  risk?: string;
  slack?: string;
  rmHrs?: string;
  flHrs?: string;
}

export interface UiCapacity {
  rollingMill?: number | null;
  finishingLine?: number | null;
  rollingMillSurplusHrs?: number | null;
  finishingLineSurplusHrs?: number | null;
  rawMaterial?: number | null;
  workforce?: number | null;
  overall?: number | null;
}

export interface UiPriorities {
  P1?: number;
  P2?: number;
  P3?: number;
  P1Value?: string;
  P2Value?: string;
  P3Value?: string;
}

export interface UiApprovalOption {
  label: string;
  key: string;
  hint?: string;
}

export interface UiApprovalRequest {
  orderId: string;
  product?: string;
  customer?: string;
  customerTier?: string;
  value?: string;
  recommendation?: string;
  options?: UiApprovalOption[];
  funnelResults?: Array<{ layer: number; name: string; passed: boolean; detail: string }>;
  reasoning?: string;
}

export interface UiPayload {
  phase?: string | null;
  agents?: UiAgentStatus[] | null;
  orders?: UiOrder[] | null;
  capacity?: UiCapacity | null;
  priorities?: UiPriorities | null;
  approvalRequest?: UiApprovalRequest | null;
  totalOrders?: number | null;
  totalValue?: string | null;
  bottleneck?: string | null;
  complete?: boolean | null;
  capacityImpact?: UiCapacityImpact | null;
  transferOrders?: UiTransferOrder[] | null;
}

// --- Capacity Impact Types (Rework 7) ---

export interface UiCapacityImpactDimension {
  current: number;
  projected: number;
}

export interface UiCapacityImpactPlant {
  name: string;
  rollingMill: UiCapacityImpactDimension;
  finishingLine: UiCapacityImpactDimension;
  overall: UiCapacityImpactDimension;
}

export interface UiCapacityImpact {
  senderPlant: UiCapacityImpactPlant;
  receiverPlant: UiCapacityImpactPlant;
}

// --- Transfer Order Types (Rework 7) ---

export interface UiTransferOrder {
  orderId: string;
  product: string;
  customer: string;
  customerTier: string;
  value: string;
  dueDate: string;
  priority: string;
  recommendation: string;
  reasoning: string;
  funnelResults: Array<{ layer: number; name: string; passed: boolean; detail: string }>;
}
