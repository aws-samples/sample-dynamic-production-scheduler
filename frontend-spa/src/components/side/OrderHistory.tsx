import { useStore } from "@/store";
import { CheckCircle, XCircle, SkipForward } from "lucide-react";

const DECISION_CONFIG = {
  approve: { icon: CheckCircle, color: "text-emerald-400", label: "Approved" },
  reject: { icon: XCircle, color: "text-red-500", label: "Rejected" },
  skip: { icon: SkipForward, color: "text-amber-400", label: "Skipped" },
} as const;

export function OrderHistory() {
  const orderHistory = useStore((s) => s.orderHistory);

  if (orderHistory.length === 0) {
    return (
      <div className="p-4 text-sm text-slate-400">
        No order decisions yet. Decisions will appear here as orders are processed.
      </div>
    );
  }

  return (
    <div className="space-y-2 p-3">
      <h3 className="text-xs font-medium uppercase tracking-wider text-slate-400">
        Order Decisions ({orderHistory.length})
      </h3>
      <div className="space-y-1">
        {orderHistory.map((d, i) => {
          const cfg = DECISION_CONFIG[d.decision];
          const Icon = cfg.icon;
          return (
            <div
              key={`${d.orderId}-${i}`}
              className="flex items-start gap-2 rounded-lg bg-slate-750 border border-slate-700 px-3 py-2"
              data-testid={`order-decision-${d.orderId}`}
            >
              <Icon size={14} className={`mt-0.5 ${cfg.color}`} />
              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-2">
                  <span className="text-sm font-mono text-slate-200">{d.orderId}</span>
                  <span className={`text-xs ${cfg.color}`}>{cfg.label}</span>
                </div>
                {d.reasoning && (
                  <div className="text-xs text-slate-400 mt-0.5 line-clamp-2">{d.reasoning}</div>
                )}
                <div className="text-xs text-slate-500 mt-0.5">
                  {d.agentName} &middot; {new Date(d.timestamp).toLocaleTimeString()}
                </div>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
