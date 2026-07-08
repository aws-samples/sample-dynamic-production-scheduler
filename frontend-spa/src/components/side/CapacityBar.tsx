import type { CapacityDimension } from "@/types";

interface CapacityBarProps {
  dimension: CapacityDimension;
  testId: string;
}

export function CapacityBar({ dimension, testId }: CapacityBarProps) {
  const pct = dimension.available > 0
    ? Math.round((dimension.used / dimension.available) * 100)
    : 0;

  const color =
    pct >= 90 ? "bg-red-500" : pct >= 70 ? "bg-yellow-500" : "bg-green-500";

  return (
    <div className="space-y-1">
      <div className="flex items-center justify-between text-xs">
        <span className="text-slate-300">{dimension.label}</span>
        <span className="text-slate-400">
          {dimension.used}/{dimension.available} {dimension.unit} ({pct}%)
        </span>
      </div>
      <div
        className="h-2 w-full rounded-full bg-slate-700"
        role="progressbar"
        aria-valuenow={pct}
        aria-valuemin={0}
        aria-valuemax={100}
        aria-label={`${dimension.label} utilization`}
        data-testid={testId}
      >
        <div
          className={`h-full rounded-full transition-all ${color}`}
          style={{ width: `${Math.min(pct, 100)}%` }}
        />
      </div>
    </div>
  );
}
