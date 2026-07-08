import { useStore } from "@/store";

export function CascadeImpactView() {
  const capacity = useStore((s) => s.capacity);

  if (!capacity) {
    return (
      <div className="p-4 text-sm text-gray-400">
        No cascade data available yet.
      </div>
    );
  }

  const dimensions = [
    capacity.rollingMill,
    capacity.finishingLine,
    capacity.materialTons,
    capacity.operatorHours,
  ];

  return (
    <div className="space-y-3 p-3">
      <h3 className="text-xs font-medium uppercase tracking-wider text-gray-500">
        Cascade Impact
      </h3>
      {dimensions.map((dim) => {
        const pct = dim.available > 0 ? (dim.used / dim.available) * 100 : 0;
        const barColor =
          pct >= dim.thresholdPct * 100
            ? "bg-red-500"
            : pct >= 70
              ? "bg-amber-500"
              : "bg-emerald-500";
        return (
          <div key={dim.label} data-testid={`cascade-dim-${dim.label}`}>
            <div className="flex justify-between text-xs text-gray-600 mb-1">
              <span>{dim.label}</span>
              <span>
                {dim.used.toFixed(1)} / {dim.available.toFixed(1)} {dim.unit}
              </span>
            </div>
            <div className="h-2 rounded-full bg-zinc-700">
              <div
                className={`h-2 rounded-full ${barColor}`}
                style={{ width: `${Math.min(pct, 100)}%` }}
              />
            </div>
          </div>
        );
      })}
      {capacity.bottleneck && (
        <div className="text-xs text-amber-400 mt-2">
          Bottleneck: {capacity.bottleneck}
        </div>
      )}
    </div>
  );
}
