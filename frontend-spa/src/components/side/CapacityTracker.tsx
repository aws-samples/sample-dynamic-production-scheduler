import { useState } from "react";
import { useStore } from "@/store";
import { CapacityBar } from "./CapacityBar";

export function CapacityTracker() {
  const capacity = useStore((s) => s.capacity);
  const [showDetails, setShowDetails] = useState(false);

  if (!capacity) {
    return (
      <div className="p-4 text-sm text-slate-400">
        Waiting for capacity data...
      </div>
    );
  }

  const dimensions = [
    { key: "rolling-mill", dim: capacity.rollingMill },
    { key: "finishing-line", dim: capacity.finishingLine },
    { key: "material-tons", dim: capacity.materialTons },
    { key: "operator-hours", dim: capacity.operatorHours },
  ];

  return (
    <div className="space-y-3 p-4">
      <h3 className="text-xs font-semibold uppercase tracking-wider text-slate-400">
        Capacity
      </h3>
      {dimensions.map((d) => (
        <CapacityBar
          key={d.key}
          dimension={d.dim}
          testId={`tracker-${d.key}-bar`}
        />
      ))}
      <p className="text-xs text-slate-300">
        Bottleneck: <span className="text-slate-100 font-medium">{capacity.bottleneck}</span>
      </p>
      <button
        data-testid="tracker-details-toggle"
        className="min-h-11 min-w-11 text-xs text-blue-400 underline hover:text-blue-300"
        onClick={() => setShowDetails(!showDetails)}
      >
        {showDetails ? "Hide details" : "Show details"}
      </button>
      {showDetails && (
        <table className="w-full text-xs text-slate-300">
          <thead>
            <tr className="border-b border-slate-700 text-left text-slate-400">
              <th className="pb-1">Dimension</th>
              <th className="pb-1">Used</th>
              <th className="pb-1">Available</th>
              <th className="pb-1">%</th>
            </tr>
          </thead>
          <tbody>
            {dimensions.map((d) => {
              const pct = d.dim.available > 0
                ? Math.round((d.dim.used / d.dim.available) * 100)
                : 0;
              return (
                <tr key={d.key} className="border-b border-slate-700">
                  <td className="py-1">{d.dim.label}</td>
                  <td className="py-1">{d.dim.used} {d.dim.unit}</td>
                  <td className="py-1">{d.dim.available} {d.dim.unit}</td>
                  <td className="py-1">{pct}%</td>
                </tr>
              );
            })}
          </tbody>
        </table>
      )}
    </div>
  );
}
