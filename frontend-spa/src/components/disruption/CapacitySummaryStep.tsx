import { useStore } from "@/store";
import { PLANT_DISPLAY_NAMES } from "@/types";
import { CheckCircle2, ArrowRight } from "lucide-react";

function utilColor(pct: number): string {
  if (pct >= 85) return "text-red-600";
  if (pct >= 70) return "text-amber-600";
  return "text-emerald-600";
}

function barBg(pct: number): string {
  if (pct >= 85) return "bg-red-500";
  if (pct >= 70) return "bg-amber-500";
  return "bg-emerald-500";
}

function DimensionRow({ label, current }: { label: string; current: number }) {
  return (
    <div className="space-y-1">
      <div className="flex items-center justify-between">
        <span className="text-sm text-gray-600">{label}</span>
        <span className={`text-sm font-bold ${utilColor(current)}`}>{current.toFixed(1)}%</span>
      </div>
      <div className="h-3 w-full rounded-full bg-gray-200">
        <div className={`h-3 rounded-full transition-all ${barBg(current)}`} style={{ width: `${Math.min(current, 100)}%` }} />
      </div>
    </div>
  );
}

export function CapacitySummaryStep() {
  const impact = useStore((s) => s.disruption?.capacityImpact);
  const disruptedPlant = useStore((s) => s.disruption?.plant);
  const orderHistory = useStore((s) => s.orderHistory);
  const setCurrentView = useStore((s) => s.setCurrentView);
  const clearDisruption = useStore((s) => s.clearDisruption);
  const addNotification = useStore((s) => s.addNotification);
  const planner = useStore((s) => s.planner);

  const receiverPlantId = disruptedPlant === "Florida" ? "Ohio" : "Florida";
  const receiverLabel = PLANT_DISPLAY_NAMES[receiverPlantId];

  const absorbed = orderHistory.filter((o) => o.decision === "approve").length;
  const deferred = orderHistory.filter((o) => o.decision === "reject").length;
  const skipped = orderHistory.filter((o) => o.decision === "skip").length;

  function handleReturnToDashboard() {
    addNotification({
      id: crypto.randomUUID(),
      type: "disruption",
      title: "Disruption Response Complete",
      message: `${absorbed} orders transferred, ${deferred} deferred. See dashboard for updated utilization.`,
      timestamp: new Date().toISOString(),
      acknowledged: false,
      plant: planner?.plant ?? "Florida",
    });
    clearDisruption();
    setCurrentView("dashboard");
  }

  return (
    <div className="flex flex-col items-center gap-8 py-8" data-testid="capacity-summary-step">
      <div className="flex h-14 w-14 items-center justify-center rounded-full bg-blue-100">
        <CheckCircle2 size={28} className="text-blue-600" />
      </div>
      <h2 className="text-xl font-semibold text-gray-900">{receiverLabel} Plant — Final Capacity</h2>

      {/* Stats */}
      <div className="flex gap-6">
        <div className="text-center">
          <p className="text-2xl font-bold text-emerald-600">{absorbed}</p>
          <p className="text-xs text-gray-500">Orders Absorbed</p>
        </div>
        <div className="text-center">
          <p className="text-2xl font-bold text-amber-600">{deferred}</p>
          <p className="text-xs text-gray-500">Orders Deferred</p>
        </div>
        {skipped > 0 && (
          <div className="text-center">
            <p className="text-2xl font-bold text-gray-500">{skipped}</p>
            <p className="text-xs text-gray-500">Skipped</p>
          </div>
        )}
      </div>

      {/* Capacity gauges */}
      {impact ? (
        <div className="w-full max-w-lg rounded-xl border border-gray-200 bg-white p-6 shadow-sm space-y-4">
          <h3 className="text-sm font-semibold text-gray-700">{receiverLabel} Utilization After All Decisions</h3>
          <DimensionRow label="Rolling Mill" current={impact.receiverPlant.rollingMill.current} />
          <DimensionRow label="Finishing Line" current={impact.receiverPlant.finishingLine.current} />
          <DimensionRow label="Overall" current={impact.receiverPlant.overall.current} />
        </div>
      ) : (
        <p className="text-sm text-gray-400">No capacity data available.</p>
      )}

      <button
        onClick={handleReturnToDashboard}
        className="flex items-center gap-2 rounded-lg bg-blue-600 px-8 py-3 text-sm font-semibold text-white shadow-sm hover:bg-blue-500"
        data-testid="return-to-dashboard-btn"
      >
        Return to Dashboard <ArrowRight size={16} />
      </button>
    </div>
  );
}
