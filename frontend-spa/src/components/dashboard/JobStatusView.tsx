import { useState } from "react";
import { useStore } from "@/store";
import { SummaryCard } from "./SummaryCard";
import type { ProductionOrder } from "@/types";
import { Package, CalendarClock } from "lucide-react";
import { PLANT_DISPLAY_NAMES } from "@/types";
import type { PlantId } from "@/types";

export function JobStatusView() {
  const facilityData = useStore((s) => s.facilityData);
  const [showHistorical, setShowHistorical] = useState(false);
  const [sortCol, setSortCol] = useState<keyof ProductionOrder>("dueDate");
  const [sortAsc, setSortAsc] = useState(true);
  const orders = facilityData?.orders ?? [];
  const active = orders.filter((o) => !["Completed", "Cancelled"].includes(o.status));
  const historical = orders.filter((o) => ["Completed", "Cancelled"].includes(o.status));
  const displayed = showHistorical ? historical : active;
  const sorted = [...displayed].sort((a, b) => {
    const av = a[sortCol] ?? "";
    const bv = b[sortCol] ?? "";
    return (sortAsc ? 1 : -1) * String(av).localeCompare(String(bv), undefined, { numeric: true });
  });

  const dueThisWeek = active.filter((o) => {
    const d = new Date(o.dueDate);
    const end = new Date();
    end.setDate(end.getDate() + 7);
    return d <= end;
  }).length;

  function handleSort(col: keyof ProductionOrder) {
    if (sortCol === col) setSortAsc(!sortAsc);
    else { setSortCol(col); setSortAsc(true); }
  }

  return (
    <div data-testid="job-status-view" className="space-y-6">
      <div className="grid grid-cols-2 gap-4">
        <SummaryCard
          label="Active Orders"
          value={active.length}
          icon={<Package size={20} className="text-cyan-400" />}
          iconBg="bg-cyan-500/10"
          valueColor="text-slate-100"
        />
        <SummaryCard
          label="Due This Week"
          value={dueThisWeek}
          icon={<CalendarClock size={20} className="text-amber-400" />}
          iconBg="bg-amber-500/10"
          valueColor={dueThisWeek > 5 ? "text-amber-400" : "text-slate-100"}
        />
      </div>

      {/* Controls */}
      <div className="flex flex-wrap items-center gap-3">
        <div className="flex gap-1.5">
          <button
            onClick={() => setShowHistorical(false)}
            className={`rounded-lg px-4 py-2 text-[13px] font-medium transition-all duration-200 ${
              !showHistorical
                ? "bg-cyan-500/15 text-cyan-400 shadow-sm shadow-cyan-500/10"
                : "text-slate-400 hover:bg-white/[0.04] hover:text-slate-300"
            }`}
            data-testid="active-orders-tab"
          >Active Orders</button>
          <button
            onClick={() => setShowHistorical(true)}
            className={`rounded-lg px-4 py-2 text-[13px] font-medium transition-all duration-200 ${
              showHistorical
                ? "bg-cyan-500/15 text-cyan-400 shadow-sm shadow-cyan-500/10"
                : "text-slate-400 hover:bg-white/[0.04] hover:text-slate-300"
            }`}
            data-testid="historical-toggle"
          >Historical</button>
        </div>
      </div>

      {/* Table */}
      <div className="overflow-x-auto glass-card overflow-hidden">
        <table className="w-full" data-testid="orders-table">
          <thead>
            <tr className="border-b border-white/[0.06]">
              {([
                ["orderId", "Order ID"],
                ["productFamily", "Product"],
                ["quantity", "Qty"],
                ["dueDate", "Due Date"],
                ["customerName", "Customer"],
                ["customerTier", "Tier"],
                ["priority", "Priority"],
              ] as [keyof ProductionOrder, string][]).map(([col, label]) => (
                <th
                  key={col}
                  onClick={() => handleSort(col)}
                  className="cursor-pointer px-4 py-3 text-left text-[11px] font-semibold uppercase tracking-wider text-slate-500 hover:text-slate-300 transition-colors"
                >
                  {label}
                  {sortCol === col && <span className="ml-1 text-cyan-400">{sortAsc ? "↑" : "↓"}</span>}
                </th>
              ))}
            </tr>
          </thead>
          <tbody className="divide-y divide-white/[0.04]">
            {sorted.map((o) => (
              <tr key={o.orderId} className="hover:bg-white/[0.02] transition-colors duration-150">
                <td className="px-4 py-3 text-sm font-medium text-cyan-400 font-mono">
                  {o.orderId}
                  {o.transferredFrom && (
                    <span
                      className="ml-2 inline-flex items-center rounded-full bg-violet-500/10 px-2 py-0.5 text-[10px] font-medium text-violet-400"
                      data-testid={`transferred-in-badge-${o.orderId}`}
                    >
                      ↓ From {PLANT_DISPLAY_NAMES[o.transferredFrom as PlantId] ?? o.transferredFrom}
                    </span>
                  )}
                </td>
                <td className="px-4 py-3 text-sm text-slate-300">{o.productFamily}</td>
                <td className="px-4 py-3 text-sm text-slate-300 font-mono">{o.quantity.toLocaleString()}</td>
                <td className="px-4 py-3 text-sm text-slate-300 font-mono">
                  {o.dueDate}
                  {new Date(o.dueDate) < new Date() && !["Completed", "Cancelled"].includes(o.status) && (
                    <span className="ml-1.5 inline-flex items-center rounded-full bg-red-500/10 px-2 py-0.5 text-[10px] font-medium text-red-400">
                      Past Due
                    </span>
                  )}
                </td>
                <td className="px-4 py-3 text-sm text-slate-300">{o.customerName}</td>
                <td className="px-4 py-3"><TierBadge tier={o.customerTier} /></td>
                <td className="px-4 py-3"><PriorityBadge priority={o.priority} /></td>
              </tr>
            ))}
            {sorted.length === 0 && (
              <tr>
                <td colSpan={7} className="px-4 py-12 text-center text-sm text-slate-600">
                  No orders found
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}

function TierBadge({ tier }: { tier: string }) {
  const styles: Record<string, string> = {
    Tier1: "bg-emerald-500/10 text-emerald-400",
    Tier2: "bg-cyan-500/10 text-cyan-400",
    Tier3: "bg-slate-500/10 text-slate-400",
  };
  return (
    <span className={`inline-flex rounded-full px-2.5 py-0.5 text-[11px] font-medium ${styles[tier] ?? "bg-slate-500/10 text-slate-400"}`}>
      {tier}
    </span>
  );
}

function PriorityBadge({ priority }: { priority: string | null }) {
  if (!priority) return <span className="text-sm text-slate-600">—</span>;
  const styles: Record<string, string> = {
    P1: "bg-red-500/10 text-red-400 ring-1 ring-red-500/20",
    P2: "bg-amber-500/10 text-amber-400 ring-1 ring-amber-500/20",
    P3: "bg-slate-500/10 text-slate-400 ring-1 ring-slate-500/20",
  };
  return (
    <span className={`inline-flex rounded-md px-2 py-0.5 text-[11px] font-bold tracking-wide ${styles[priority] ?? "bg-slate-500/10 text-slate-400"}`}>
      {priority}
    </span>
  );
}
