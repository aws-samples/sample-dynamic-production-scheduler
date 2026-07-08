/**
 * Cascade impact visualization — simple node-and-line graph.
 * Left: disruption events (Florida shutdown, delay decisions, funnel outcomes).
 * Right: affected orders with status pills.
 * Lines connect events to the orders they impact.
 */

import { useStore } from "@/store";
import type { TransferRequest } from "@/types";

interface EventNode {
  id: string;
  label: string;
  severity: "critical" | "high" | "medium";
  affected: number;
}

interface OrderNode {
  id: string;
  label: string;
  status: "transferred" | "delayed" | "rejected" | "pending";
  value: number;
}

interface Link {
  eventId: string;
  orderId: string;
}

function buildGraph(transfers: TransferRequest[]) {
  const events: EventNode[] = [
    { id: "disruption", label: "Florida Plant Shutdown", severity: "critical", affected: transfers.length },
  ];

  const delayed = transfers.filter((t) => t.recommendation === "delay");
  const approved = transfers.filter((t) => t.status === "approved");
  const pending = transfers.filter((t) => t.status === "submitted_for_review" || t.status === "pending_approval");
  const declined = transfers.filter((t) => t.status === "declined");

  if (delayed.length > 0) events.push({ id: "delay-opt", label: "Delay Optimization", severity: "high", affected: delayed.length });
  if (approved.length + pending.length > 0) events.push({ id: "funnel-pass", label: "Funnel — Transferable", severity: "medium", affected: approved.length + pending.length });
  if (declined.length > 0) events.push({ id: "funnel-fail", label: "Funnel — Non-transferable", severity: "high", affected: declined.length });

  const orders: OrderNode[] = transfers.map((t) => ({
    id: t.orderId,
    label: t.orderId,
    status: t.recommendation === "delay" ? "delayed" : t.status === "approved" ? "transferred" : t.status === "declined" ? "rejected" : "pending",
    value: t.order.orderValue,
  }));

  const links: Link[] = [];
  transfers.forEach((t) => {
    links.push({ eventId: "disruption", orderId: t.orderId });
    if (t.recommendation === "delay") links.push({ eventId: "delay-opt", orderId: t.orderId });
    else if (t.status === "declined") links.push({ eventId: "funnel-fail", orderId: t.orderId });
    else links.push({ eventId: "funnel-pass", orderId: t.orderId });
  });

  return { events, orders, links };
}

const sevColor = { critical: "#ef4444", high: "#f59e0b", medium: "#06b6d4" };
const sevBg = { critical: "bg-red-500/20 text-red-400 border-red-500/30", high: "bg-amber-500/20 text-amber-400 border-amber-500/30", medium: "bg-cyan-500/20 text-cyan-400 border-cyan-500/30" };
const statusPill: Record<string, string> = {
  transferred: "bg-emerald-500/20 text-emerald-400",
  delayed: "bg-violet-500/20 text-violet-400",
  rejected: "bg-red-500/20 text-red-400",
  pending: "bg-amber-500/20 text-amber-400",
};
const statusText: Record<string, string> = { transferred: "Transfer", delayed: "Delayed", rejected: "Rejected", pending: "Pending" };

export function DisruptionFlowSankey() {
  const transfers = useStore((s) => s.transferRequests);
  if (transfers.length === 0) return null;

  const { events, orders, links } = buildGraph(transfers);

  const eventSpacing = 72;
  const orderSpacing = 36;
  const svgPad = 16;

  // We'll render events and orders as HTML divs in two columns,
  // then overlay an SVG for the connecting lines.

  return (
    <div className="glass-card overflow-hidden">
      <div className="border-b border-white/[0.06] px-5 py-3">
        <div className="flex items-center justify-between">
          <div>
            <h3 className="text-sm font-semibold text-slate-200">Cascade Impact Visualization</h3>
            <p className="text-[11px] text-slate-500 mt-0.5">Events and their affected transfer orders</p>
          </div>
          <div className="flex items-center gap-3 text-[10px] text-slate-500">
            <span className="flex items-center gap-1"><span className="inline-block h-1.5 w-4 rounded-full bg-emerald-500/50" /> Transferred</span>
            <span className="flex items-center gap-1"><span className="inline-block h-1.5 w-4 rounded-full bg-violet-500/50" /> Delayed</span>
            <span className="flex items-center gap-1"><span className="inline-block h-1.5 w-4 rounded-full bg-amber-500/50" /> Pending</span>
            <span className="flex items-center gap-1"><span className="inline-block h-1.5 w-4 rounded-full bg-red-500/50" /> Rejected</span>
          </div>
        </div>
      </div>

      <div className="relative p-5">
        <div className="grid grid-cols-[280px_1fr_220px] gap-0 min-h-[200px]" id="cascade-grid">
          {/* Left: Event nodes */}
          <div className="flex flex-col gap-3 z-10">
            {events.map((ev) => (
              <div
                key={ev.id}
                data-event={ev.id}
                className={`rounded-lg border px-3 py-2.5 ${sevBg[ev.severity]} backdrop-blur-sm`}
              >
                <div className="flex items-center gap-2">
                  <span className="h-2 w-2 rounded-full" style={{ backgroundColor: sevColor[ev.severity] }} />
                  <span className="text-xs font-semibold">{ev.label}</span>
                </div>
                <p className="text-[10px] opacity-60 mt-1">{ev.affected} affected</p>
              </div>
            ))}
          </div>

          {/* Middle: SVG lines */}
          <div className="relative">
            <svg className="absolute inset-0 w-full h-full" preserveAspectRatio="none">
              {/* Lines are drawn via CSS/JS positioning — we use a simple approach:
                  each link gets a line from left edge to right edge at proportional Y positions */}
              {links.map((link, i) => {
                const eventIdx = events.findIndex((e) => e.id === link.eventId);
                const orderIdx = orders.findIndex((o) => o.id === link.orderId);
                if (eventIdx < 0 || orderIdx < 0) return null;

                const ey = (eventIdx * eventSpacing) + 28 + svgPad;
                const oy = (orderIdx * orderSpacing) + 14 + svgPad;
                const orderStatus = orders[orderIdx]?.status;
                const lineColor = orderStatus === "delayed" ? "rgba(139,92,246,0.2)"
                  : orderStatus === "transferred" ? "rgba(16,185,129,0.2)"
                  : orderStatus === "rejected" ? "rgba(239,68,68,0.2)"
                  : "rgba(245,158,11,0.18)";

                return (
                  <line
                    key={`${link.eventId}-${link.orderId}-${i}`}
                    x1="0"
                    y1={ey}
                    x2="100%"
                    y2={oy}
                    stroke={lineColor}
                    strokeWidth="1.5"
                    strokeDasharray="4 3"
                    className="animate-flow-line"
                  />
                );
              })}
            </svg>
          </div>

          {/* Right: Order nodes */}
          <div className="flex flex-col gap-1 z-10">
            {orders.map((order) => (
              <div
                key={order.id}
                data-order={order.id}
                className="flex items-center gap-2 rounded-md bg-white/[0.03] border border-white/[0.06] px-2.5 py-1.5 hover:bg-white/[0.06] transition-colors"
              >
                <span className="h-1.5 w-1.5 rounded-full" style={{
                  backgroundColor: order.status === "transferred" ? "#10b981" : order.status === "delayed" ? "#8b5cf6" : order.status === "rejected" ? "#ef4444" : "#f59e0b",
                }} />
                <span className="text-[11px] font-mono font-medium text-slate-300 flex-1">{order.label}</span>
                <span className={`rounded-full px-1.5 py-0.5 text-[9px] font-medium ${statusPill[order.status]}`}>
                  {statusText[order.status]}
                </span>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}
