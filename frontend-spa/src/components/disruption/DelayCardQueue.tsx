import { useState, useEffect, useRef } from "react";
import { useStore } from "@/store";
import { sendMessage } from "@/lib/streaming";
import { submitTransfers } from "@/lib/transferApi";
import { DelayCandidateCard } from "./DelayCandidateCard";
import { Loader2, ArrowRight, Clock, Package } from "lucide-react";

/**
 * Purely DynamoDB-driven delay candidate queue.
 *
 * All candidates come from `store.disruption.delayCandidates` (populated by
 * the state poller from DynamoDB). Decisions are tracked locally in the store
 * and sent to the orchestrator as fire-and-forget messages.
 *
 * No dependency on chat messages or orchestrator `approvalRequest` UI payloads.
 */
export function DelayCardQueue({ readOnly = false }: { readOnly?: boolean }) {
  const delayCandidates = useStore((s) => s.disruption?.delayCandidates ?? []);
  const currentDelayIndex = useStore((s) => s.disruption?.currentDelayIndex ?? 0);
  const orderHistory = useStore((s) => s.orderHistory);
  const isTyping = useStore((s) => s.chat.isAgentTyping);
  const setPhase = useStore((s) => s.setDisruptionPhase);
  const advanceDelay = useStore((s) => s.advanceDelayIndex);

  const [proceeding, setProceeding] = useState(false);

  const approved = orderHistory.filter((o) => o.decision === "approve").length;
  const rejected = orderHistory.filter((o) => o.decision === "reject").length;
  const allDone = delayCandidates.length > 0 && currentDelayIndex >= delayCandidates.length;

  // Auto-transition: when all candidates are reviewed, move to constraint funnel
  const autoTransitioned = useRef(false);
  useEffect(() => {
    if (readOnly) return;
    if (allDone && !autoTransitioned.current && !proceeding) {
      autoTransitioned.current = true;
      setPhase("constraint_funnel");
      // Send a single summary to the orchestrator at phase boundary
      const decisions = delayCandidates.map((c) => {
        const dec = orderHistory.find((o) => o.orderId === c.orderId);
        return `${c.orderId}: ${dec?.decision?.toUpperCase() || "SKIPPED"}`;
      }).join(", ");
      const msg = `[DECISION_SUMMARY] Delay optimization complete. Decisions: ${decisions}.\nProceed to constraint funnel phase. Call update_session_phase("round2_funnel") and invoke_constraint_matching for all Florida orders. Do NOT re-process individual delay decisions — they are already recorded.`;
      useStore.getState().addUserMessage(crypto.randomUUID(), msg);
      sendMessage(msg).catch(() => {});
    }
  }, [allDone, proceeding, setPhase, delayCandidates, orderHistory]);

  async function handleProceedToFunnel() {
    setProceeding(true);
    setPhase("constraint_funnel");
    const decided = delayCandidates.slice(0, currentDelayIndex).map((c) => {
      const dec = orderHistory.find((o) => o.orderId === c.orderId);
      return `${c.orderId}: ${dec?.decision?.toUpperCase() || "SKIPPED"}`;
    }).join(", ");
    const msg = `[DECISION_SUMMARY] Delay optimization complete (${currentDelayIndex}/${delayCandidates.length} reviewed). Decisions: ${decided || "none"}.\nSkipping remaining candidates. Proceed to constraint funnel. Call update_session_phase("round2_funnel") and invoke_constraint_matching. Do NOT re-process delay decisions.`;
    useStore.getState().addUserMessage(crypto.randomUUID(), msg);
    sendMessage(msg).catch(() => {});
    setProceeding(false);
  }

  return (
    <div className="flex flex-1 flex-col gap-4" data-testid="delay-card-queue">
      <div>
        <h3 className="text-sm font-semibold text-gray-700">Delay Optimization</h3>
        <p className="text-xs text-gray-500 mt-1">
          Review low-priority orders at the receiving plant that can be delayed to free capacity for incoming disrupted orders.
        </p>
      </div>

      {/* Decision tally */}
      {(approved > 0 || rejected > 0) && (
        <div className="flex gap-3">
          <div className="flex items-center gap-1.5 rounded-full bg-emerald-50 px-3 py-1 text-xs font-medium text-emerald-700">
            <Package size={12} /> {approved} delayed
          </div>
          <div className="flex items-center gap-1.5 rounded-full bg-yellow-50 px-3 py-1 text-xs font-medium text-yellow-700">
            <Clock size={12} /> {rejected} kept
          </div>
        </div>
      )}

      <div className="space-y-4 max-h-[55vh] overflow-y-auto">
        {/* Already-decided candidates */}
        {delayCandidates.slice(0, currentDelayIndex).map((c, idx) => {
          const decision = orderHistory.find((o) => o.orderId === c.orderId);
          if (!decision) return null;
          return (
            <DelayCandidateCard
              key={`decided-${c.orderId}`}
              ui={{
                phase: "delay_optimization",
                approvalRequest: {
                  orderId: c.orderId,
                  product: c.order.productFamily,
                  customer: c.order.customerName,
                  customerTier: c.order.customerTier,
                  value: c.order.orderValue ? `$${c.order.orderValue.toLocaleString()}` : "",
                  recommendation: c.impactSummary || c.freedCapacity,
                  options: [],
                },
              }}
              candidateNum={idx + 1}
              totalCandidates={delayCandidates.length}
            />
          );
        })}

        {/* Current candidate awaiting decision */}
        {!allDone && delayCandidates.length > 0 && (() => {
          const c = delayCandidates[currentDelayIndex];
          if (!c) return null;
          // Already decided (e.g. poller hasn't advanced yet)
          if (orderHistory.some((o) => o.orderId === c.orderId)) return null;
          return (
            <DelayCandidateCard
              key={`current-${c.orderId}`}
              ui={{
                phase: "delay_optimization",
                approvalRequest: {
                  orderId: c.orderId,
                  product: c.order.productFamily,
                  customer: c.order.customerName,
                  customerTier: c.order.customerTier,
                  value: c.order.orderValue ? `$${c.order.orderValue.toLocaleString()}` : "",
                  recommendation: c.impactSummary || c.freedCapacity,
                  options: [
                    { label: "APPROVE", key: "approve", hint: "Delay this order" },
                    { label: "REJECT", key: "reject", hint: "Keep on schedule" },
                  ],
                },
              }}
              candidateNum={currentDelayIndex + 1}
              totalCandidates={delayCandidates.length}
              onDecision={async (decision) => {
                const store = useStore.getState();
                const plant = store.disruption?.plant || "Florida";
                store.addOrderDecision({
                  orderId: c.orderId,
                  decision: decision as "approve" | "reject",
                  agentName: "User",
                  timestamp: new Date().toISOString(),
                  reasoning: null,
                });
                advanceDelay();

                // Update live capacity panel — delay approval frees capacity at receiver
                if (decision === "approve" && store.disruption?.capacityImpact) {
                  const freed = c.freedCapacity || "";
                  const rmMatch = freed.match(/RM\s*\+?([\d.]+)/);
                  const flMatch = freed.match(/FL\s*\+?([\d.]+)/);
                  const rmFreed = rmMatch ? parseFloat(rmMatch[1]!) : 0;
                  const flFreed = flMatch ? parseFloat(flMatch[1]!) : 0;
                  // Convert freed hours to percentage points (rough: 148 hrs total RM, 152 hrs FL)
                  const rmPctDelta = rmFreed > 0 ? (rmFreed / 148) * 100 : 0;
                  const flPctDelta = flFreed > 0 ? (flFreed / 152) * 100 : 0;
                  const prev = store.disruption.capacityImpact;
                  store.setDisruptionCapacityImpact({
                    ...prev,
                    receiverPlant: {
                      ...prev.receiverPlant,
                      rollingMill: { ...prev.receiverPlant.rollingMill, projected: Math.max(0, prev.receiverPlant.rollingMill.projected - rmPctDelta) },
                      finishingLine: { ...prev.receiverPlant.finishingLine, projected: Math.max(0, prev.receiverPlant.finishingLine.projected - flPctDelta) },
                    },
                  });
                }

                // If approved, write to transfers table so both plants see it
                if (decision === "approve") {
                  submitTransfers(
                    [{
                      orderId: c.orderId,
                      product: c.order.productFamily,
                      customer: c.order.customerName,
                      customerTier: c.order.customerTier,
                      value: c.order.orderValue ? `$${c.order.orderValue.toLocaleString()}` : "",
                      dueDate: c.order.dueDate,
                      priority: c.order.priority || "P3",
                      recommendation: "delay",
                      reasoning: c.impactSummary || c.freedCapacity,
                      funnelResults: [],
                    }],
                    plant,
                    plant === "Florida" ? "Ohio" : "Florida",
                  ).catch(() => {});
                }

                // Fire-and-forget removed — decisions are frontend-only.
                // The orchestrator only receives phase transition summaries.
              }}
            />
          );
        })()}

        {/* All candidates exhausted */}
        {allDone && (
          <div className="rounded-lg border border-emerald-200 bg-emerald-50 p-4 text-center">
            <p className="text-sm font-medium text-emerald-800">
              All {delayCandidates.length} delay candidates reviewed.
            </p>
            <p className="text-xs text-emerald-600 mt-1">
              {approved} delayed, {rejected} kept on schedule.
            </p>
          </div>
        )}

        {/* No candidates loaded yet */}
        {delayCandidates.length === 0 && (
          <div className="flex items-center gap-2 text-sm text-gray-500 py-8 justify-center">
            <Loader2 size={16} className="animate-spin" /> Loading delay candidates...
          </div>
        )}
      </div>

      {isTyping && (
        <div className="flex items-center gap-2 text-sm text-blue-600">
          <Loader2 size={16} className="animate-spin" /> Processing...
        </div>
      )}

      {!isTyping && delayCandidates.length > 0 && !allDone && (
        <div className="space-y-3">
          {(approved + rejected > 0) && (
            <button
              onClick={handleProceedToFunnel}
              disabled={proceeding}
              className="flex items-center gap-2 rounded-lg bg-blue-600 px-6 py-2.5 text-sm font-semibold text-white shadow-sm hover:bg-blue-500 disabled:opacity-40"
              data-testid="proceed-to-funnel-btn"
            >
              {proceeding ? "Starting..." : "Skip remaining & Proceed to Constraint Funnel"}
              {!proceeding && <ArrowRight size={16} />}
            </button>
          )}
        </div>
      )}
    </div>
  );
}
