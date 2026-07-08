import { useStore } from "@/store";
import { Check } from "lucide-react";
import type { DisruptionPhase } from "@/types";

const STEPS: { phase: DisruptionPhase; label: string }[] = [
  { phase: "round1", label: "Intelligence Gathering" },
  { phase: "delay_optimization", label: "Delay Optimization" },
  { phase: "constraint_funnel", label: "Constraint Funnel" },
  { phase: "capacity_summary", label: "Capacity Summary" },
  { phase: "complete", label: "Complete" },
];

const PHASE_ORDER: DisruptionPhase[] = ["landing", "round1", "delay_optimization", "constraint_funnel", "capacity_summary", "complete"];

function phaseIndex(p: DisruptionPhase): number {
  return PHASE_ORDER.indexOf(p);
}

export function PhaseStepper({ onPhaseClick }: { onPhaseClick?: (phase: DisruptionPhase) => void }) {
  const currentPhase = useStore((s) => s.disruption?.phase ?? "landing");
  const currentIdx = phaseIndex(currentPhase);

  return (
    <nav aria-label="Disruption workflow progress" data-testid="phase-stepper" className="mb-6">
      <ol className="flex items-center gap-2">
        {STEPS.map((step, i) => {
          const stepIdx = phaseIndex(step.phase);
          const isComplete = currentIdx > stepIdx;
          const isCurrent = currentPhase === step.phase;
          const isClickable = isComplete && onPhaseClick;

          return (
            <li key={step.phase} className="flex flex-1 items-center">
              <div
                className={`flex flex-1 flex-col items-center gap-1 ${isClickable ? "cursor-pointer" : ""}`}
                onClick={isClickable ? () => onPhaseClick(step.phase) : undefined}
              >
                <div
                  className={`flex h-8 w-8 items-center justify-center rounded-full text-xs font-semibold transition-colors ${
                    isComplete
                      ? "bg-emerald-500 text-white hover:bg-emerald-600"
                      : isCurrent
                        ? "bg-blue-600 text-white"
                        : "bg-gray-200 text-gray-500"
                  }`}
                >
                  {isComplete ? <Check size={14} /> : i + 1}
                </div>
                <span
                  className={`text-xs text-center font-medium ${
                    isCurrent ? "text-blue-700" : isComplete ? "text-emerald-700 hover:underline" : "text-gray-400"
                  }`}
                >
                  {step.label}
                </span>
              </div>
              {i < STEPS.length - 1 && (
                <div
                  className={`mx-1 h-0.5 flex-1 transition-colors ${
                    currentIdx > stepIdx ? "bg-emerald-400" : "bg-gray-200"
                  }`}
                />
              )}
            </li>
          );
        })}
      </ol>
    </nav>
  );
}
