import { useStore } from "@/store";
import { sendMessage } from "@/lib/streaming";
import { submitTransfers } from "@/lib/transferApi";
import { DelayCandidateCard } from "./DelayCandidateCard";
import { Loader2, ArrowRight, CheckCircle, XCircle, SkipForward } from "lucide-react";
import { KanbanBoard } from "./KanbanBoard";

/**
 * Purely DynamoDB-driven constraint funnel view.
 *
 * All funnel orders come from `store.disruption.funnelOrders` (populated by
 * the state poller from DynamoDB). Decisions are tracked locally and sent
 * to the orchestrator as fire-and-forget.
 */
export function ConstraintFunnelView({ readOnly = false }: { readOnly?: boolean }) {
  const funnelOrders = useStore((s) => s.disruption?.funnelOrders ?? []);
  const currentFunnelIndex = useStore((s) => s.disruption?.currentFunnelIndex ?? 0);
  const funnelDecisions = useStore((s) => s.disruption?.funnelDecisions ?? {});
  const isTyping = useStore((s) => s.chat.isAgentTyping);
  const setPhase = useStore((s) => s.setDisruptionPhase);
  const advanceFunnel = useStore((s) => s.advanceFunnelIndex);
  const addFunnelDecision = useStore((s) => s.addDisruptionFunnelDecision);

  const disruptedPlant = useStore((s) => s.disruption?.plant ?? "Florida");
  const receivingPlant = disruptedPlant === "Florida" ? "Ohio" : "Florida";

  const approvedCount = Object.values(funnelDecisions).filter((d) => d === "approved").length;
  const rejectedCount = Object.values(funnelDecisions).filter((d) => d === "rejected").length;
  const skippedCount = Object.values(funnelDecisions).filter((d) => d === "skipped").length;
  const allDone = funnelOrders.length > 0 && currentFunnelIndex >= funnelOrders.length;

  function handleComplete() {
    setPhase("complete");
    const approved = Object.entries(funnelDecisions).filter(([, d]) => d === "approved").map(([id]) => id);
    const rejected = Object.entries(funnelDecisions).filter(([, d]) => d === "rejected").map(([id]) => id);
    const skipped = Object.entries(funnelDecisions).filter(([, d]) => d === "skipped").map(([id]) => id);
    const msg = `[DECISION_SUMMARY] Constraint funnel complete. Approved: ${approved.join(", ") || "none"}. Rejected: ${rejected.join(", ") || "none"}. Skipped: ${skipped.join(", ") || "none"}.\nAll rounds complete. Call update_session_phase("summary") and generate a disruption response summary. Do NOT re-process individual funnel decisions — they are already recorded. Then call update_session_phase("complete").`;
    useStore.getState().addUserMessage(crypto.randomUUID(), msg);
    sendMessage(msg).catch(() => {});
  }

  return (
    <div className="flex flex-1 flex-col gap-4" data-testid="constraint-funnel-view">
      <div>
        <h3 className="text-sm font-semibold text-gray-700">Constraint Funnel — Order Rerouting</h3>
        <p className="text-xs text-gray-500 mt-1">
          Each order runs through a 4-layer constraint check (equipment, materials, workforce, schedule). Approve, reject, or skip each recommendation.
        </p>
      </div>

      {(approvedCount > 0 || rejectedCount > 0 || skippedCount > 0) && (
        <div className="flex gap-3">
          <div className="flex items-center gap-1.5 rounded-full bg-emerald-50 px-3 py-1 text-xs font-medium text-emerald-700">
            <CheckCircle size={12} /> {approvedCount} rerouted
          </div>
          <div className="flex items-center gap-1.5 rounded-full bg-red-50 px-3 py-1 text-xs font-medium text-red-700">
            <XCircle size={12} /> {rejectedCount} rejected
          </div>
          {skippedCount > 0 && (
            <div className="flex items-center gap-1.5 rounded-full bg-gray-100 px-3 py-1 text-xs font-medium text-gray-600">
              <SkipForward size={12} /> {skippedCount} skipped
            </div>
          )}
        </div>
      )}

      <div className="space-y-4 max-h-[55vh] overflow-y-auto">
        {funnelOrders.slice(0, currentFunnelIndex).map((fo, idx) => {
          const dec = funnelDecisions[fo.orderId];
          if (!dec || dec === "pending") return null;
          return (
            <DelayCandidateCard
              key={`decided-${fo.orderId}`}
              ui={{ phase: "constraint_funnel", approvalRequest: {
                orderId: fo.orderId, product: fo.order.productFamily, customer: fo.order.customerName,
                customerTier: fo.order.customerTier, value: fo.order.orderValue ? `$${fo.order.orderValue.toLocaleString()}` : "",
                recommendation: fo.recommendation, reasoning: fo.reasoning,
                funnelResults: fo.funnelResults.map((f) => ({ layer: f.layer, name: f.name, passed: f.passed, detail: f.detail })),
                options: [],
              }}}
              candidateNum={idx + 1}
              totalCandidates={funnelOrders.length}
            />
          );
        })}

        {!readOnly && !allDone && funnelOrders.length > 0 && (() => {
          const fo = funnelOrders[currentFunnelIndex];
          if (!fo) return null;
          if (funnelDecisions[fo.orderId] && funnelDecisions[fo.orderId] !== "pending") return null;
          return (
            <DelayCandidateCard
              key={`current-${fo.orderId}`}
              ui={{ phase: "constraint_funnel", approvalRequest: {
                orderId: fo.orderId, product: fo.order.productFamily, customer: fo.order.customerName,
                customerTier: fo.order.customerTier, value: fo.order.orderValue ? `$${fo.order.orderValue.toLocaleString()}` : "",
                recommendation: fo.recommendation, reasoning: fo.reasoning,
                funnelResults: fo.funnelResults.map((f) => ({ layer: f.layer, name: f.name, passed: f.passed, detail: f.detail })),
                options: [
                  { label: "APPROVE", key: "approve", hint: `Transfer to ${receivingPlant}` },
                  { label: "REJECT", key: "reject", hint: "Cannot accommodate" },
                  { label: "SKIP", key: "skip", hint: "Decide later" },
                ],
              }}}
              candidateNum={currentFunnelIndex + 1}
              totalCandidates={funnelOrders.length}
              onDecision={async (decision) => {
                const store = useStore.getState();
                const plant = store.disruption?.plant || "Florida";
                const column = decision === "approve" ? "approved" as const : decision === "reject" ? "rejected" as const : "skipped" as const;
                addFunnelDecision(fo.orderId, column);
                store.addOrderDecision({ orderId: fo.orderId, decision: decision as "approve" | "reject" | "skip", agentName: "User", timestamp: new Date().toISOString(), reasoning: null });
                advanceFunnel();

                // Update live capacity panel — transfer approval consumes capacity at receiver
                if (decision === "approve" && store.disruption?.capacityImpact) {
                  const utilLayer = fo.funnelResults.find((f) => f.name === "Utilization");
                  const rmMatch = utilLayer?.detail?.match(/RM[:\s]*([\d.]+)/i);
                  const flMatch = utilLayer?.detail?.match(/FL[:\s]*([\d.]+)/i);
                  // Convert consumed hours to percentage points
                  const rmConsumed = rmMatch ? parseFloat(rmMatch[1]!) : (fo.order.orderValue > 0 ? fo.order.orderValue / 5000 : 5);
                  const flConsumed = flMatch ? parseFloat(flMatch[1]!) : (fo.order.orderValue > 0 ? fo.order.orderValue / 8000 : 3);
                  const rmPctDelta = (rmConsumed / 148) * 100;
                  const flPctDelta = (flConsumed / 152) * 100;
                  const prev = store.disruption.capacityImpact;
                  store.setDisruptionCapacityImpact({
                    ...prev,
                    receiverPlant: {
                      ...prev.receiverPlant,
                      rollingMill: { ...prev.receiverPlant.rollingMill, projected: Math.min(100, prev.receiverPlant.rollingMill.projected + rmPctDelta) },
                      finishingLine: { ...prev.receiverPlant.finishingLine, projected: Math.min(100, prev.receiverPlant.finishingLine.projected + flPctDelta) },
                    },
                  });
                }

                if (decision === "approve") {
                  submitTransfers([{
                    orderId: fo.orderId, product: fo.order.productFamily, customer: fo.order.customerName,
                    customerTier: fo.order.customerTier, value: fo.order.orderValue ? `$${fo.order.orderValue.toLocaleString()}` : "",
                    dueDate: fo.order.dueDate, priority: fo.order.priority || "P3",
                    recommendation: fo.recommendation, reasoning: fo.reasoning,
                    funnelResults: fo.funnelResults.map((f) => ({ layer: f.layer, name: f.name, passed: f.passed, detail: f.detail })),
                  }], plant, plant === "Florida" ? "Ohio" : "Florida").catch(() => {});
                }
                // Decision is frontend-only — no fire-and-forget to orchestrator.
                // The orchestrator receives a summary at phase transition.
              }}
            />
          );
        })()}

        {allDone && (
          <div className="rounded-lg border border-emerald-200 bg-emerald-50 p-4 text-center">
            <p className="text-sm font-medium text-emerald-800">All {funnelOrders.length} constraint funnel orders reviewed.</p>
            <p className="text-xs text-emerald-600 mt-1">{approvedCount} rerouted, {rejectedCount} rejected{skippedCount > 0 ? `, ${skippedCount} skipped` : ""}.</p>
          </div>
        )}

        {funnelOrders.length === 0 && (
          <div className="flex flex-col items-center gap-3 text-sm text-gray-500 py-8">
            <Loader2 size={20} className="animate-spin text-blue-500" />
            <p className="font-medium text-gray-700">Running constraint funnel analysis...</p>
            <p className="text-xs text-gray-400 max-w-sm text-center">
              The Constraint Matching Agent is evaluating each order against equipment, material, workforce, and schedule constraints at the {receivingPlant} plant. This typically takes 30–60 seconds.
            </p>
          </div>
        )}
      </div>

      {(approvedCount > 0 || rejectedCount > 0 || skippedCount > 0) && (
        <div className="mt-2">
          <h4 className="text-xs font-medium text-gray-500 uppercase tracking-wide mb-2">Order Status Board</h4>
          <KanbanBoard />
        </div>
      )}

      {isTyping && (
        <div className="flex items-center gap-2 text-sm text-blue-600">
          <Loader2 size={16} className="animate-spin" /> Processing...
        </div>
      )}

      {!readOnly && !isTyping && funnelOrders.length > 0 && (approvedCount + rejectedCount + skippedCount > 0) && (
        <button onClick={handleComplete} className="flex items-center gap-2 rounded-lg bg-emerald-600 px-6 py-2.5 text-sm font-semibold text-white shadow-sm hover:bg-emerald-500" data-testid="complete-workflow-btn">
          {allDone ? "Finish & View Summary" : "Skip remaining & Finish"} <ArrowRight size={16} />
        </button>
      )}
    </div>
  );
}
