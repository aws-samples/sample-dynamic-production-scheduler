import { useStore } from "@/store";

export function ScorecardView() {
  const orderHistory = useStore((s) => s.orderHistory);

  const approved = orderHistory.filter((d) => d.decision === "approve").length;
  const rejected = orderHistory.filter((d) => d.decision === "reject").length;
  const skipped = orderHistory.filter((d) => d.decision === "skip").length;
  const total = orderHistory.length;

  if (total === 0) {
    return (
      <div className="p-4 text-sm text-gray-400">
        No scorecard data yet. Process orders to see the scorecard.
      </div>
    );
  }

  const cards = [
    { label: "Approved", value: approved, color: "text-emerald-400", bg: "bg-emerald-950/30" },
    { label: "Rejected", value: rejected, color: "text-red-500", bg: "bg-red-50/30" },
    { label: "Skipped", value: skipped, color: "text-amber-400", bg: "bg-amber-950/30" },
    { label: "Total", value: total, color: "text-gray-700", bg: "bg-gray-100/50" },
  ];

  return (
    <div className="space-y-3 p-3">
      <h3 className="text-xs font-medium uppercase tracking-wider text-gray-500">
        Decision Scorecard
      </h3>
      <div className="grid grid-cols-2 gap-2">
        {cards.map((c) => (
          <div
            key={c.label}
            className={`rounded px-3 py-2 ${c.bg}`}
            data-testid={`scorecard-${c.label.toLowerCase()}`}
          >
            <div className={`text-xl font-bold ${c.color}`}>{c.value}</div>
            <div className="text-xs text-gray-500">{c.label}</div>
          </div>
        ))}
      </div>
      {total > 0 && (
        <div className="h-3 flex rounded-full overflow-hidden bg-zinc-700">
          {approved > 0 && (
            <div
              className="bg-emerald-500"
              style={{ width: `${(approved / total) * 100}%` }}
            />
          )}
          {rejected > 0 && (
            <div
              className="bg-red-500"
              style={{ width: `${(rejected / total) * 100}%` }}
            />
          )}
          {skipped > 0 && (
            <div
              className="bg-amber-500"
              style={{ width: `${(skipped / total) * 100}%` }}
            />
          )}
        </div>
      )}
    </div>
  );
}
