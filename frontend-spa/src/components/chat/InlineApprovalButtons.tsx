import { useState } from "react";
import { sendMessage } from "@/lib/streaming";
import { useStore } from "@/store";
import type { ParsedApprovalOrder, DecisionOption } from "@/lib/responseParser";
import { CheckCircle, XCircle, PenLine, Clock, HelpCircle } from "lucide-react";

interface InlineApprovalButtonsProps {
  orders: ParsedApprovalOrder[];
}

const COLOR_MAP: Record<DecisionOption["color"], { active: string; idle: string; icon: typeof CheckCircle }> = {
  green:  { active: "bg-emerald-500/25 text-emerald-300 ring-2 ring-emerald-500/40", idle: "border border-emerald-500/30 bg-emerald-500/10 text-emerald-400 hover:bg-emerald-500/20 transition-all duration-200", icon: CheckCircle },
  red:    { active: "bg-red-500/25 text-red-300 ring-2 ring-red-500/40",             idle: "border border-red-500/30 bg-red-500/10 text-red-400 hover:bg-red-500/20 transition-all duration-200",                 icon: XCircle },
  amber:  { active: "bg-amber-500/25 text-amber-300 ring-2 ring-amber-500/40",       idle: "border border-amber-500/30 bg-amber-500/10 text-amber-400 hover:bg-amber-500/20 transition-all duration-200",           icon: Clock },
  blue:   { active: "bg-cyan-500/25 text-cyan-300 ring-2 ring-cyan-500/40",           idle: "border border-cyan-500/30 bg-cyan-500/10 text-cyan-400 hover:bg-cyan-500/20 transition-all duration-200",               icon: PenLine },
  zinc:   { active: "bg-white/[0.08] text-slate-200 ring-2 ring-white/[0.12]",        idle: "border border-white/[0.06] bg-white/[0.04] text-slate-400 hover:bg-white/[0.08] transition-all duration-200",           icon: HelpCircle },
};

export function InlineApprovalButtons({ orders }: InlineApprovalButtonsProps) {
  const [decisions, setDecisions] = useState<Record<string, string>>({});
  const [submitted, setSubmitted] = useState(false);
  const [sending, setSending] = useState(false);

  const handleDecision = (orderId: string, key: string) => {
    setDecisions((prev) => ({ ...prev, [orderId]: key }));
  };

  const handleSubmitAll = async () => {
    const parts: string[] = [];
    for (const order of orders) {
      const key = decisions[order.orderId];
      if (!key) continue;
      parts.push(`${key.toUpperCase()} ${order.orderId}`);
    }
    if (parts.length === 0) return;

    setSending(true);
    const message = parts.join(", ");

    const store = useStore.getState();
    for (const order of orders) {
      const key = decisions[order.orderId];
      if (key) {
        const mapped = /approve|reroute|transfer|accept/i.test(key) ? "approve"
          : /reject|cancel|infeasible/i.test(key) ? "reject"
          : "skip";
        store.addOrderDecision({
          orderId: order.orderId,
          decision: mapped,
          agentName: "User",
          timestamp: new Date().toISOString(),
          reasoning: key,
        });
      }
    }

    store.addUserMessage(crypto.randomUUID(), message);
    await sendMessage(message);
    setSubmitted(true);
    setSending(false);
  };

  const allDecided = orders.every((o) => decisions[o.orderId]);
  const decidedCount = orders.filter((o) => decisions[o.orderId]).length;

  if (submitted) {
    return (
      <div className="mt-3 rounded-lg border border-white/[0.06] bg-slate-800/80 p-3">
        <p className="text-xs text-emerald-400 font-medium">
          Decisions submitted for {orders.length} order(s)
        </p>
        <div className="mt-1 space-y-1">
          {orders.map((o) => {
            const key = decisions[o.orderId] || "";
            const opt = o.options.find((op) => op.key === key);
            const cm = COLOR_MAP[opt?.color || "zinc"];
            const Icon = cm.icon;
            return (
              <div key={o.orderId} className="flex items-center gap-2 text-xs text-slate-400">
                <Icon size={12} className="shrink-0" />
                <span className="font-mono">{o.orderId}</span>
                <span className="text-slate-500">
                  {opt ? `${opt.label}${opt.hint ? ` (${opt.hint})` : ""}` : key}
                </span>
              </div>
            );
          })}
        </div>
      </div>
    );
  }

  return (
    <div className="mt-3 space-y-2">
      {orders.map((order) => {
        const chosen = decisions[order.orderId];
        return (
          <div
            key={order.orderId}
            className="rounded-lg border border-white/[0.06] bg-slate-800/80 p-3 space-y-2"
          >
            {/* Order header */}
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <span className="text-sm font-mono font-medium text-slate-100">
                  {order.orderId}
                </span>
                {order.product && <span className="text-xs text-slate-400">{order.product}</span>}
                {order.customer && <span className="text-xs text-slate-500">{order.customer}</span>}
              </div>
              {order.value && <span className="text-xs text-slate-400">{order.value}</span>}
            </div>

            {/* Dynamic decision buttons */}
            <div className="flex flex-wrap gap-2">
              {order.options.map((opt) => {
                const isChosen = chosen === opt.key;
                const cm = COLOR_MAP[opt.color];
                const Icon = cm.icon;
                return (
                  <button
                    key={opt.key}
                    type="button"
                    data-testid={`inline-${opt.key}-${order.orderId}`}
                    aria-label={`${opt.label} ${order.orderId}${opt.hint ? ` — ${opt.hint}` : ""}`}
                    onClick={() => handleDecision(order.orderId, opt.key)}
                    className={`min-h-9 flex items-center gap-1.5 rounded-md px-3 py-1.5 text-xs font-medium transition-all duration-200 ${
                      isChosen ? cm.active : cm.idle
                    }`}
                  >
                    <Icon size={12} />
                    <span>{opt.label}</span>
                    {opt.hint && <span className="opacity-70 text-[10px]">({opt.hint})</span>}
                  </button>
                );
              })}
            </div>
          </div>
        );
      })}

      <button
        type="button"
        data-testid="submit-all-decisions"
        disabled={!allDecided || sending}
        onClick={handleSubmitAll}
        className="w-full min-h-11 rounded-lg bg-gradient-to-r from-cyan-500 to-teal-500 px-4 py-2 text-sm font-medium text-white hover:from-cyan-400 hover:to-teal-400 disabled:opacity-40 disabled:cursor-not-allowed transition-all duration-200"
      >
        {sending
          ? "Submitting..."
          : `Submit Decisions (${decidedCount}/${orders.length})`}
      </button>
    </div>
  );
}
