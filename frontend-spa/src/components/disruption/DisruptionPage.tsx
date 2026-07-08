import { useState, useEffect } from "react";
import { useStore } from "@/store";
import { PhaseStepper } from "./PhaseStepper";
import { DisruptionLanding } from "./DisruptionLanding";
import { Round1SplitView } from "./Round1SplitView";
import { DelayCardQueue } from "./DelayCardQueue";
import { ConstraintFunnelView } from "./ConstraintFunnelView";
import { CapacityImpactPanel } from "./CapacityImpactPanel";
import { CapacitySummaryStep } from "./CapacitySummaryStep";
import { WhatIfChat } from "./WhatIfChat";
import { SafeMarkdown } from "@/lib/markdown";
import { CheckCircle2, Loader2 } from "lucide-react";
import type { DisruptionPhase } from "@/types";

export function DisruptionPage() {
  const disruption = useStore((s) => s.disruption);
  const clearDisruption = useStore((s) => s.clearDisruption);
  const setCurrentView = useStore((s) => s.setCurrentView);
  const addNotification = useStore((s) => s.addNotification);
  const planner = useStore((s) => s.planner);
  const [viewPhase, setViewPhase] = useState<DisruptionPhase | null>(null);

  // No active disruption — show landing
  if (!disruption) {
    return (
      <div className="flex flex-1 flex-col overflow-hidden bg-gray-50" data-testid="disruption-page">
        <DisruptionLanding />
      </div>
    );
  }

  function handleFinish() {
    addNotification({
      id: crypto.randomUUID(),
      type: "disruption",
      title: "Disruption Response Complete",
      message: disruption?.summaryText ?? "Disruption workflow completed successfully.",
      timestamp: new Date().toISOString(),
      acknowledged: false,
      plant: planner?.plant ?? "Florida",
    });
    clearDisruption();
    setCurrentView("transfer-dashboard");
  }

  const displayPhase = viewPhase ?? disruption.phase;
  const isViewingPast = viewPhase !== null && viewPhase !== disruption.phase;
  const displayIsThreeColumn = displayPhase === "delay_optimization" || displayPhase === "constraint_funnel";

  return (
    <div className="flex flex-1 flex-col overflow-hidden bg-gray-50" data-testid="disruption-page">
      <div className="flex-1 overflow-y-auto">
        {displayIsThreeColumn ? (
          <div className="mx-auto max-w-[1400px] p-6 lg:p-8">
            <PhaseStepper onPhaseClick={(p) => setViewPhase(p === disruption.phase ? null : p)} />
            {isViewingPast && (
              <button onClick={() => setViewPhase(null)} className="mb-3 text-xs text-blue-600 hover:underline">
                ← Back to current phase ({disruption.phase.replace(/_/g, " ")})
              </button>
            )}
            <div className="grid grid-cols-[1fr_320px] gap-6 min-h-[400px]">
              <div>
                {displayPhase === "delay_optimization" && <DelayCardQueue readOnly={isViewingPast} />}
                {displayPhase === "constraint_funnel" && <ConstraintFunnelView readOnly={isViewingPast} />}
              </div>
              <aside className="sticky top-24 self-start">
                <CapacityImpactPanel />
              </aside>
            </div>
          </div>
        ) : (
          <div className="mx-auto max-w-6xl p-6 lg:p-8">
            <PhaseStepper onPhaseClick={(p) => setViewPhase(p === disruption.phase ? null : p)} />
            {isViewingPast && (
              <button onClick={() => setViewPhase(null)} className="mb-3 text-xs text-blue-600 hover:underline">
                ← Back to current phase ({disruption.phase.replace(/_/g, " ")})
              </button>
            )}
            <div className="min-h-[400px]">
              {displayPhase === "round1" && <Round1SplitView readOnly={isViewingPast} />}
              {displayPhase === "capacity_summary" && <CapacitySummaryStep />}
              {displayPhase === "complete" && (
                <CompleteSummary summaryText={disruption.summaryText} onFinish={handleFinish} />
              )}
            </div>
          </div>
        )}
      </div>
      {disruption.phase !== "complete" && disruption.phase !== "capacity_summary" && <WhatIfChat />}
    </div>
  );
}

function CompleteSummary({
  summaryText,
  onFinish,
}: {
  summaryText: string | null;
  onFinish: () => void;
}) {
  const disruption = useStore((s) => s.disruption);
  const orderHistory = useStore((s) => s.orderHistory);

  // Build a local summary from store data if the orchestrator hasn't provided one after 5s
  const [localSummary, setLocalSummary] = useState<string | null>(null);
  useEffect(() => {
    if (summaryText) return;
    const timer = setTimeout(() => {
      if (!disruption) return;
      const totalOrders = disruption.impactResults.length;
      const p1 = disruption.impactResults.filter((o) => o.priority === "P1").length;
      const p2 = disruption.impactResults.filter((o) => o.priority === "P2").length;
      const p3 = disruption.impactResults.filter((o) => o.priority === "P3" || !o.priority).length;
      const totalValue = disruption.impactResults.reduce((s, o) => s + o.orderValue, 0);
      const delaysApproved = orderHistory.filter((o) => o.decision === "approve" && disruption.delayCandidates.some((c) => c.orderId === o.orderId)).length;
      const delaysRejected = orderHistory.filter((o) => o.decision === "reject" && disruption.delayCandidates.some((c) => c.orderId === o.orderId)).length;
      const funnelApproved = Object.values(disruption.funnelDecisions).filter((d) => d === "approved").length;
      const funnelRejected = Object.values(disruption.funnelDecisions).filter((d) => d === "rejected").length;
      const bottleneck = disruption.capacityResults?.bottleneck || "Unknown";

      setLocalSummary(
        `## Disruption Response Summary\n\n` +
        `**${totalOrders} orders** analyzed from the ${disruption.plant} plant disruption, ` +
        `with a total portfolio value of **$${totalValue.toLocaleString()}**.\n\n` +
        `**Priority Distribution:** ${p1} P1 (Critical), ${p2} P2 (High), ${p3} P3 (Standard)\n\n` +
        `**Bottleneck:** ${bottleneck}\n\n` +
        `### Delay Optimization\n` +
        `- ${delaysApproved} orders delayed to free capacity\n` +
        `- ${delaysRejected} orders kept on schedule\n\n` +
        `### Constraint Funnel\n` +
        `- ${funnelApproved} orders approved for transfer\n` +
        `- ${funnelRejected} orders rejected (capacity constraints)\n`
      );
    }, 5000);
    return () => clearTimeout(timer);
  }, [summaryText, disruption, orderHistory]);

  const displayText = summaryText || localSummary;

  return (
    <div className="flex flex-col items-center gap-6 py-12" data-testid="disruption-complete">
      <div className="flex h-16 w-16 items-center justify-center rounded-full bg-emerald-100">
        <CheckCircle2 size={32} className="text-emerald-600" />
      </div>
      <h2 className="text-xl font-semibold text-gray-900">Disruption Response Complete</h2>
      {!displayText && (
        <div className="flex items-center gap-2 text-sm text-blue-600">
          <Loader2 size={16} className="animate-spin" /> Generating summary...
        </div>
      )}
      {displayText && (
        <div className="max-w-2xl rounded-lg border border-gray-200 bg-white p-6 shadow-sm">
          <div className="prose prose-sm prose-gray max-w-none">
            <SafeMarkdown content={displayText} />
          </div>
        </div>
      )}
      <button
        onClick={onFinish}
        className="rounded-lg bg-blue-600 px-8 py-3 text-sm font-semibold text-white shadow-sm hover:bg-blue-500"
        data-testid="disruption-finish-btn"
      >
        Move to Transfer Dashboard
      </button>
    </div>
  );
}
