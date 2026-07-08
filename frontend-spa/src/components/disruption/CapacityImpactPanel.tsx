import { useStore } from "@/store";
import { PLANT_DISPLAY_NAMES } from "@/types";

function barColor(pct: number): string {
  if (pct >= 85) return "bg-red-500";
  if (pct >= 70) return "bg-amber-500";
  return "bg-emerald-500";
}

function projectedBarColor(pct: number): string {
  if (pct >= 85) return "bg-red-300";
  if (pct >= 70) return "bg-amber-300";
  return "bg-cyan-400";
}

function pctColor(pct: number): string {
  if (pct >= 85) return "text-red-600";
  if (pct >= 70) return "text-amber-600";
  return "text-emerald-600";
}

function DualGauge({ label, current, projected }: { label: string; current: number; projected: number }) {
  const changed = Math.abs(projected - current) > 0.1;
  return (
    <div className="space-y-1.5">
      <div className="flex items-center justify-between">
        <span className="text-xs font-medium text-gray-600">{label}</span>
        <span className={`text-xs font-semibold tabular-nums ${pctColor(projected)}`}>
          {projected.toFixed(1)}%
        </span>
      </div>
      {/* Current bar */}
      <div className="relative">
        <div className="flex items-center gap-2">
          <span className="text-[10px] text-gray-400 w-12 shrink-0">Current</span>
          <div className="h-2 flex-1 rounded-full bg-gray-100">
            <div
              className={`h-2 rounded-full transition-all duration-500 ${barColor(current)}`}
              style={{ width: `${Math.min(current, 100)}%` }}
            />
          </div>
          <span className="text-[10px] text-gray-400 w-10 text-right tabular-nums">{current.toFixed(0)}%</span>
        </div>
      </div>
      {/* Projected bar */}
      <div className="relative">
        <div className="flex items-center gap-2">
          <span className="text-[10px] text-gray-400 w-12 shrink-0">After</span>
          <div className="h-2 flex-1 rounded-full bg-gray-100">
            <div
              className={`h-2 rounded-full transition-all duration-500 ${projectedBarColor(projected)}`}
              style={{ width: `${Math.min(Math.max(projected, 0), 100)}%` }}
            />
          </div>
          <span className={`text-[10px] w-10 text-right tabular-nums ${changed ? (projected < current ? "text-emerald-600 font-semibold" : "text-red-600 font-semibold") : "text-gray-400"}`}>
            {projected.toFixed(0)}%
          </span>
        </div>
      </div>
    </div>
  );
}

export function CapacityImpactPanel() {
  const impact = useStore((s) => s.disruption?.capacityImpact);
  const disruptedPlant = useStore((s) => s.disruption?.plant);
  const phase = useStore((s) => s.disruption?.phase);
  const isComplete = phase === "complete" || phase === "capacity_summary";

  if (!impact) {
    return (
      <div className="rounded-xl border border-gray-200 bg-white p-4 shadow-sm" data-testid="capacity-impact-panel">
        <h3 className="text-sm font-semibold text-gray-700 mb-2">Live Capacity</h3>
        <p className="text-xs text-gray-400">Capacity data will appear after Round 1 analysis.</p>
      </div>
    );
  }

  const receiverPlantId = disruptedPlant === "Florida" ? "Ohio" : "Florida";
  const receiverLabel = `${PLANT_DISPLAY_NAMES[receiverPlantId]} Plant Utilization`;
  const r = impact.receiverPlant;

  return (
    <div className="rounded-xl border border-gray-200 bg-white p-4 shadow-sm space-y-4" data-testid="capacity-impact-panel">
      <h3 className="text-sm font-semibold text-gray-700">
        {isComplete ? "Final Capacity" : "Live Capacity"}
      </h3>
      <p className="text-[10px] text-gray-400 -mt-2">{receiverLabel}</p>
      <DualGauge label="Rolling Mill" current={r.rollingMill.current} projected={r.rollingMill.projected} />
      <DualGauge label="Finishing Line" current={r.finishingLine.current} projected={r.finishingLine.projected} />
      {r.overall.current > 0 && (
        <DualGauge label="Overall" current={r.overall.current} projected={r.overall.projected} />
      )}
    </div>
  );
}
