import { useStore } from "@/store";
import type { WorkflowPhase } from "@/types";

const PHASES: { key: WorkflowPhase; label: string }[] = [
  { key: "disruption_intake", label: "Intake" },
  { key: "impact_assessment", label: "Impact" },
  { key: "capacity_analysis", label: "Capacity" },
  { key: "delay_optimization", label: "Delays" },
  { key: "constraint_matching", label: "Funnel" },
  { key: "what_if", label: "What-If" },
  { key: "summary", label: "Summary" },
];

const phaseOrder = PHASES.map((p) => p.key);

export function PhaseProgressBar() {
  const current = useStore((s) => s.session.currentPhase);
  const currentIdx = phaseOrder.indexOf(current);

  return (
    <div
      data-testid="phase-progress-bar"
      className="flex items-center gap-1 border-b border-slate-700 bg-slate-800 px-3 py-2 overflow-x-auto"
    >
      {PHASES.map((phase, i) => {
        const isComplete = currentIdx > i;
        const isActive = current === phase.key;
        const isFuture = currentIdx < i || current === "idle" || current === "complete";

        return (
          <div key={phase.key} className="flex items-center gap-1">
            <div
              className={`rounded-full px-2 py-0.5 text-[10px] font-medium whitespace-nowrap ${
                isActive
                  ? "bg-blue-500 text-white"
                  : isComplete
                    ? "bg-green-700 text-green-200"
                    : isFuture
                      ? "bg-slate-700 text-slate-400"
                      : "bg-slate-700 text-slate-400"
              }`}
            >
              {isComplete ? "✓ " : ""}
              {phase.label}
            </div>
            {i < PHASES.length - 1 && (
              <span className="text-slate-500 text-[10px]">›</span>
            )}
          </div>
        );
      })}
    </div>
  );
}
