import { useState } from "react";
import { useStore } from "@/store";
import { sendMessage } from "@/lib/streaming";
import { DisruptionConfirmCard } from "./DisruptionConfirmCard";
import { Round1ResultsCard } from "./Round1ResultsCard";
import { Loader2 } from "lucide-react";

export function Round1SplitView({ readOnly = false }: { readOnly?: boolean }) {
  const disruption = useStore((s) => s.disruption);
  const messages = useStore((s) => s.chat.messages);
  const isTyping = useStore((s) => s.chat.isAgentTyping);
  const setPhase = useStore((s) => s.setDisruptionPhase);
  const [proceeding, setProceeding] = useState(false);

  if (!disruption) return null;

  const assistantMsgs = messages.filter((m) => m.role === "assistant" && m.content.length > 0);

  // Only check for round1 completion in messages AFTER the first one
  const postConfirmMsgs = assistantMsgs.slice(1);

  // Round 1 is complete when any assistant message has the right phase
  // Check all assistant messages (not just post-confirm) because the
  // orchestrator may return Round 1 results in the first response.
  const round1Complete = assistantMsgs.some(
    (m) => m.uiData?.phase === "round1_complete" || m.uiData?.phase === "round1_analysis" ||
      (!m.uiData?.phase && postConfirmMsgs.includes(m) && /impact\s*assessment|priority\s*distribution|capacity\s*analysis|round\s*1\s*(?:summary|complete)/i.test(m.content)),
  );

  // Check if user already confirmed
  const userConfirmed = messages.some((m, i) =>
    m.role === "user" && i > messages.indexOf(assistantMsgs[0]!),
  );
  const isConfirmation =
    assistantMsgs.length >= 1 &&
    !round1Complete &&
    !userConfirmed &&
    (assistantMsgs[0]?.uiData?.phase === "confirmation" ||
     (!assistantMsgs[0]?.uiData?.phase && /shall I (?:begin|proceed)|please confirm|confirm.*(?:ready|proceed|begin)/i.test(assistantMsgs[0]?.content ?? "")));

  // Find the message with Round 1 results (uiData-driven with text fallback)
  const round1Msg = assistantMsgs.find(
    (m) => m.uiData?.phase === "round1_complete" || m.uiData?.phase === "round1_analysis" ||
      (!m.uiData?.phase && postConfirmMsgs.includes(m) && /impact\s*assessment|priority\s*distribution|capacity\s*analysis|round\s*1\s*(?:summary|complete)/i.test(m.content)),
  );

  // Build uiData from store (DynamoDB source of truth) when available,
  // falling back to message uiData for fields the store doesn't have.
  const impactResults = useStore((s) => s.disruption?.impactResults ?? []);
  const capacityResults = useStore((s) => s.disruption?.capacityResults);
  const enrichedUiData = (() => {
    const base = round1Msg?.uiData ?? {};
    // Always prefer store data when available — DynamoDB is source of truth
    if (impactResults.length > 0 || capacityResults) {
      const p1 = impactResults.filter((o) => o.priority === "P1");
      const p2 = impactResults.filter((o) => o.priority === "P2");
      const p3 = impactResults.filter((o) => o.priority === "P3" || !o.priority);
      return {
        ...base,
        phase: "round1_complete",
        orders: impactResults.length > 0 ? impactResults.map((o) => ({
          orderId: o.orderId,
          product: o.productFamily,
          customer: o.customerName,
          customerTier: o.customerTier,
          value: `$${o.orderValue.toLocaleString()}`,
          dueDate: o.dueDate,
          priority: o.priority || "P3",
        })) : (base.orders ?? []),
        priorities: impactResults.length > 0 ? {
          P1: p1.length, P2: p2.length, P3: p3.length,
          P1Value: `$${p1.reduce((s, o) => s + o.orderValue, 0).toLocaleString()}`,
          P2Value: `$${p2.reduce((s, o) => s + o.orderValue, 0).toLocaleString()}`,
          P3Value: `$${p3.reduce((s, o) => s + o.orderValue, 0).toLocaleString()}`,
        } : base.priorities,
        totalOrders: impactResults.length > 0 ? impactResults.length : base.totalOrders,
        totalValue: impactResults.length > 0 ? `$${impactResults.reduce((s, o) => s + o.orderValue, 0).toLocaleString()}` : base.totalValue,
        capacity: capacityResults ? {
          rollingMill: capacityResults.rollingMill.used,
          finishingLine: capacityResults.finishingLine.used,
          rawMaterial: capacityResults.materialTons.used,
          workforce: capacityResults.operatorHours.used,
        } : base.capacity,
        bottleneck: capacityResults?.bottleneck ?? base.bottleneck,
      };
    }
    return base;
  })();

  async function handleProceedToRound2() {
    setProceeding(true);
    const msg = "Yes, proceed to Round 2. Begin delay optimization.";
    useStore.getState().addUserMessage(crypto.randomUUID(), msg);
    setPhase("delay_optimization");
    await sendMessage(msg);
    setProceeding(false);
  }

  // --- Render exactly ONE view based on state ---

  // State 1: No responses yet
  if (!isTyping && assistantMsgs.length === 0) {
    return (
      <div className="flex items-center justify-center py-16" data-testid="round1-split-view">
        <div className="flex items-center gap-2 text-sm text-gray-400">
          <Loader2 size={16} className="animate-spin" />
          Waiting for orchestrator response...
        </div>
      </div>
    );
  }

  // State 2: Confirmation card (orchestrator asks for confirmation)
  if (isConfirmation && !round1Complete) {
    return (
      <div className="flex flex-col gap-4" data-testid="round1-split-view">
        <DisruptionConfirmCard content={assistantMsgs[0]?.content ?? ""} plant={disruption.plant} />
        {isTyping && (
          <div className="flex items-center gap-2 text-sm text-blue-600">
            <Loader2 size={16} className="animate-spin" />
            Orchestrator is processing...
          </div>
        )}
      </div>
    );
  }

  // Also consider round1 complete if the store has both IA and CO data
  const storeHasRound1 = impactResults.length > 0 && !!capacityResults;

  // State 3: Round 1 complete — show structured results card
  // ONLY show if we actually have data (store or uiData with orders)
  const hasRealData = storeHasRound1 || (round1Msg?.uiData?.orders as unknown[] | undefined)?.length;
  if ((round1Complete || storeHasRound1) && (round1Msg || storeHasRound1) && hasRealData) {
    return (
      <div data-testid="round1-split-view">
        <Round1ResultsCard
          content={round1Msg?.content ?? "Round 1 analysis complete."}
          uiData={enrichedUiData as import("@/types").UiPayload}
          onProceed={readOnly ? undefined : handleProceedToRound2}
          proceeding={proceeding}
          receivingPlant={disruption.plant === "Florida" ? "Ohio" : "Florida"}
        />
      </div>
    );
  }

  // State 4: In-progress — show clean loading state while agents work
  return (
    <div className="flex flex-1 flex-col items-center justify-center gap-4 py-16" data-testid="round1-split-view">
      <div className="flex items-center gap-3 text-sm text-blue-600">
        <Loader2 size={18} className="animate-spin" />
        <span>Running Round 1 intelligence gathering — analyzing orders and capacity...</span>
      </div>
      <p className="text-xs text-gray-400 max-w-md text-center">
        Impact Assessment and Capacity Optimization agents are running in parallel. Results will appear automatically.
      </p>
    </div>
  );
}
