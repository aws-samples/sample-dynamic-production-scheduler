import { useStore } from "@/store";
import type { TransferRequest, TransferStatus, PlantId } from "@/types";
import {
  ArrowLeftRight,
  Check,
  X,
  Clock,
  ArrowDownToLine,
  ArrowUpFromLine,
  BarChart3,
} from "lucide-react";
import { SummaryCard } from "./SummaryCard";
import { DisruptionFlowSankey } from "./DisruptionFlowSankey";
import { NotificationBanner } from "./NotificationBanner";

const statusColor: Record<TransferStatus, string> = {
  proposed: "bg-slate-500", confirmed: "bg-violet-500", pending_approval: "bg-amber-500",
  approved: "bg-emerald-500", declined: "bg-red-500", resubmitted: "bg-violet-500",
  submitted_for_review: "bg-cyan-500",
};
const statusLabel: Record<TransferStatus, string> = {
  proposed: "Proposed", confirmed: "Confirmed", pending_approval: "Pending",
  approved: "Accepted", declined: "Declined", resubmitted: "Resubmitted",
  submitted_for_review: "In Review",
};

function useTransferStats() {
  const transfers = useStore((s) => s.transferRequests);
  const planner = useStore((s) => s.planner);
  const myPlant: PlantId = planner?.plant ?? "Florida";
  const total = transfers.length;
  const approved = transfers.filter((t) => t.status === "approved");
  const declined = transfers.filter((t) => t.status === "declined");
  const pending = transfers.filter((t) => t.status === "submitted_for_review" || t.status === "pending_approval");
  const totalValue = transfers.reduce((s, t) => s + t.order.orderValue, 0);
  return {
    total, approved: approved.length, declined: declined.length, pending: pending.length,
    totalValue,
    approvedValue: approved.reduce((s, t) => s + t.order.orderValue, 0),
    declinedValue: declined.reduce((s, t) => s + t.order.orderValue, 0),
    pendingValue: pending.reduce((s, t) => s + t.order.orderValue, 0),
    transfers, myPlant,
  };
}

export function TransferDashboardPage() {
  const stats = useTransferStats();
  if (stats.total === 0) return <EmptyState />;

  return (
    <div data-testid="transfer-dashboard-page" className="flex flex-1 flex-col overflow-hidden bg-slate-950">
      <div className="flex-1 overflow-y-auto scrollbar-thin">
        <div className="mx-auto max-w-7xl p-6 lg:p-8">
          <div className="mb-6">
            <h2 className="text-xl font-semibold text-slate-100 tracking-tight">Transfer Dashboard</h2>
            <p className="text-sm text-slate-500">Cross-plant transfer analytics and status overview</p>
          </div>

          <NotificationBanner />

          <div className="mb-6 grid grid-cols-2 gap-4 lg:grid-cols-4">
            <SummaryCard label="Total Transfers" value={stats.total} subtitle={`$${(stats.totalValue / 1000).toFixed(0)}k total value`} icon={<ArrowLeftRight size={20} className="text-cyan-400" />} iconBg="bg-cyan-500/10" />
            <SummaryCard label="Accepted" value={stats.approved} subtitle={`$${(stats.approvedValue / 1000).toFixed(0)}k value`} icon={<Check size={20} className="text-emerald-400" />} iconBg="bg-emerald-500/10" valueColor="text-emerald-400" />
            <SummaryCard label="Declined" value={stats.declined} subtitle={`$${(stats.declinedValue / 1000).toFixed(0)}k value`} icon={<X size={20} className="text-red-400" />} iconBg="bg-red-500/10" valueColor="text-red-400" />
            <SummaryCard label="Pending Review" value={stats.pending} subtitle={`$${(stats.pendingValue / 1000).toFixed(0)}k value`} icon={<Clock size={20} className="text-amber-400" />} iconBg="bg-amber-500/10" valueColor="text-amber-400" />
          </div>

          <div className="mb-6"><DisruptionFlowSankey /></div>

          <RecentTransfersTable transfers={stats.transfers} myPlant={stats.myPlant} />
        </div>
      </div>
    </div>
  );
}

function RecentTransfersTable({ transfers, myPlant }: { transfers: TransferRequest[]; myPlant: PlantId }) {
  const sorted = [...transfers].sort((a, b) => new Date(b.proposedAt).getTime() - new Date(a.proposedAt).getTime()).slice(0, 20);
  return (
    <div className="glass-card overflow-hidden" data-testid="recent-transfers-table">
      <div className="border-b border-white/[0.06] px-6 py-4">
        <p className="text-sm font-medium text-slate-300">Recent Transfers</p>
      </div>
      <div className="overflow-x-auto">
        <table className="w-full text-left text-sm">
          <thead>
            <tr className="border-b border-white/[0.04] text-xs text-slate-500">
              <th className="px-6 py-3 font-medium">Order</th>
              <th className="px-4 py-3 font-medium">Direction</th>
              <th className="px-4 py-3 font-medium">Product</th>
              <th className="px-4 py-3 font-medium">Customer</th>
              <th className="px-4 py-3 font-medium text-right">Value</th>
              <th className="px-4 py-3 font-medium">Priority</th>
              <th className="px-4 py-3 font-medium">Status</th>
              <th className="px-4 py-3 font-medium">Date</th>
            </tr>
          </thead>
          <tbody>
            {sorted.map((t) => {
              const isIn = t.order.plant !== myPlant;
              return (
                <tr key={t.id} className="border-b border-white/[0.03] hover:bg-white/[0.02]">
                  <td className="px-6 py-3 font-mono text-cyan-400">{t.orderId}</td>
                  <td className="px-4 py-3">
                    <span className={`inline-flex items-center gap-1 rounded-md px-2 py-0.5 text-[11px] font-medium ${isIn ? "bg-cyan-500/10 text-cyan-400" : "bg-violet-500/10 text-violet-400"}`}>
                      {isIn ? <><ArrowDownToLine size={10} /> In</> : <><ArrowUpFromLine size={10} /> Out</>}
                    </span>
                  </td>
                  <td className="px-4 py-3 text-slate-300">{t.order.productFamily}</td>
                  <td className="px-4 py-3 text-slate-400">{t.order.customerName}</td>
                  <td className="px-4 py-3 text-right font-mono text-slate-300">${t.order.orderValue.toLocaleString()}</td>
                  <td className="px-4 py-3">
                    {t.order.priority ? (
                      <span className={`inline-flex rounded-md px-2 py-0.5 text-[11px] font-bold ${t.order.priority === "P1" ? "bg-red-500/10 text-red-400" : t.order.priority === "P2" ? "bg-amber-500/10 text-amber-400" : "bg-slate-500/10 text-slate-400"}`}>{t.order.priority}</span>
                    ) : <span className="text-slate-600">—</span>}
                  </td>
                  <td className="px-4 py-3">
                    <span className="inline-flex items-center gap-1.5 rounded-full px-2.5 py-0.5 text-[11px] font-medium">
                      <span className={`h-1.5 w-1.5 rounded-full ${statusColor[t.status]}`} />
                      <span className={statusColor[t.status].replace("bg-", "text-").replace("-500", "-400")}>{statusLabel[t.status]}</span>
                    </span>
                  </td>
                  <td className="px-4 py-3 text-xs text-slate-500">{new Date(t.proposedAt).toLocaleDateString()}</td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </div>
  );
}

function EmptyState() {
  return (
    <div className="flex flex-1 flex-col items-center justify-center bg-slate-950 p-8">
      <div className="mx-auto mb-5 flex h-16 w-16 items-center justify-center rounded-2xl bg-slate-800/80 ring-1 ring-white/[0.06]">
        <BarChart3 size={28} className="text-slate-500" />
      </div>
      <h3 className="text-lg font-semibold text-slate-300">No Transfer Data Yet</h3>
      <p className="mt-2 max-w-sm text-center text-sm text-slate-500">
        Transfer statistics will appear here once disruption workflows generate transfer requests.
      </p>
    </div>
  );
}
