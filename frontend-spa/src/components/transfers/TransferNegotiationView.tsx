import { useState, useEffect } from "react";
import { useStore } from "@/store";
import type { TransferRequest, TransferStatus, PlantId } from "@/types";
import { PLANT_DISPLAY_NAMES } from "@/types";
import { decideTransfer, startTransferPolling, stopTransferPolling } from "@/lib/transferApi";
import { ArrowDownToLine, ArrowUpFromLine, Check, X } from "lucide-react";

const statusStyles: Record<TransferStatus, string> = {
  proposed: "bg-slate-500/10 text-slate-400",
  confirmed: "bg-violet-500/10 text-violet-400",
  pending_approval: "bg-amber-500/10 text-amber-400",
  approved: "bg-emerald-500/10 text-emerald-400",
  declined: "bg-red-500/10 text-red-400",
  resubmitted: "bg-violet-500/10 text-violet-400",
  submitted_for_review: "bg-cyan-500/10 text-cyan-400",
};

const statusLabels: Record<TransferStatus, string> = {
  proposed: "Proposed",
  confirmed: "Confirmed",
  pending_approval: "Pending Approval",
  approved: "Accepted",
  declined: "Declined",
  resubmitted: "Resubmitted",
  submitted_for_review: "Submitted for Review",
};

type Tab = "incoming" | "outgoing";

export function TransferNegotiationView() {
  const planner = useStore((s) => s.planner);
  const transferRequests = useStore((s) => s.transferRequests);
  const [activeTab, setActiveTab] = useState<Tab>("incoming");
  const [rejectingId, setRejectingId] = useState<string | null>(null);
  const [rejectReason, setRejectReason] = useState("");

  const myPlant: PlantId = planner?.plant ?? "Florida";

  useEffect(() => {
    startTransferPolling(myPlant);
    return () => stopTransferPolling();
  }, [myPlant]);

  const incoming = transferRequests.filter((t) => t.order.plant !== myPlant);
  const outgoing = transferRequests.filter((t) => t.order.plant === myPlant);

  function handleAccept(t: TransferRequest) {
    useStore.getState().acceptTransfer(t.id);
    decideTransfer(t.id, "approved").catch(() => {});
  }
  function handleRejectClick(transferId: string) { setRejectingId(transferId); setRejectReason(""); }
  function handleRejectConfirm(t: TransferRequest) {
    const reason = rejectReason.trim() || undefined;
    useStore.getState().rejectTransfer(t.id, reason);
    decideTransfer(t.id, "declined", reason).catch(() => {});
    setRejectingId(null); setRejectReason("");
  }
  function handleRejectCancel() { setRejectingId(null); setRejectReason(""); }

  return (
    <div data-testid="transfer-negotiation-view" className="flex flex-1 flex-col overflow-hidden bg-slate-950">
      <div className="flex-1 overflow-y-auto scrollbar-thin">
        <div className="mx-auto max-w-5xl p-6 lg:p-8">
          <div className="mb-6">
            <h2 className="text-xl font-semibold text-slate-100 tracking-tight">Transfer Negotiation</h2>
            <p className="text-sm text-slate-500">Manage cross-plant transfer requests for {PLANT_DISPLAY_NAMES[myPlant]}</p>
          </div>

          {/* Tabs */}
          <div className="mb-6 flex gap-1.5" data-testid="transfer-tabs">
            {([["incoming", ArrowDownToLine, incoming] as const, ["outgoing", ArrowUpFromLine, outgoing] as const]).map(([tab, Icon, list]) => (
              <button
                key={tab}
                onClick={() => setActiveTab(tab)}
                className={`flex items-center gap-2 rounded-lg px-4 py-2 text-[13px] font-medium transition-all duration-200 ${
                  activeTab === tab
                    ? "bg-cyan-500/15 text-cyan-400 shadow-sm shadow-cyan-500/10"
                    : "text-slate-400 hover:bg-white/[0.04] hover:text-slate-300"
                }`}
                data-testid={`${tab}-tab`}
              >
                <Icon size={15} />
                {tab === "incoming" ? "Incoming" : "Outgoing"} Transfers
                {list.length > 0 && (
                  <span className="ml-1 rounded-full bg-white/10 px-2 py-0.5 text-[11px]">{list.length}</span>
                )}
              </button>
            ))}
          </div>

          {/* Incoming */}
          {activeTab === "incoming" && (
            <div data-testid="incoming-transfers">
              <p className="mb-4 text-sm text-slate-500">Review these orders to include in your production schedule</p>
              {incoming.length === 0 ? (
                <div className="glass-card p-16 text-center">
                  <div className="mx-auto mb-4 flex h-14 w-14 items-center justify-center rounded-xl bg-slate-700/50">
                    <ArrowDownToLine size={24} className="text-slate-500" />
                  </div>
                  <p className="text-sm font-medium text-slate-400">No incoming transfers</p>
                  <p className="mt-1 text-xs text-slate-600">Transfer requests from other plants will appear here</p>
                </div>
              ) : (
                <div className="space-y-4">
                  {incoming.map((t) => (
                    <div key={t.id} className="glass-card-hover p-5" data-testid={`incoming-transfer-card-${t.orderId}`}>
                      <div className="flex items-center justify-between">
                        <div className="flex items-center gap-3">
                          <span className="text-sm font-semibold text-cyan-400 font-mono">{t.orderId}</span>
                          <TierBadge tier={t.order.customerTier} />
                          {t.order.priority && <PriorityBadge priority={t.order.priority} />}
                        </div>
                        <span className="text-xs text-slate-600">From {PLANT_DISPLAY_NAMES[t.order.plant as PlantId] ?? t.order.plant}</span>
                      </div>
                      <div className="mt-3 grid grid-cols-2 gap-3 text-sm sm:grid-cols-4">
                        <span className="text-slate-500">Product: <span className="text-slate-300">{t.order.productFamily}</span></span>
                        <span className="text-slate-500">Customer: <span className="text-slate-300">{t.order.customerName}</span></span>
                        <span className="text-slate-500">Value: <span className="text-slate-300">${t.order.orderValue.toLocaleString()}</span></span>
                        <span className="text-slate-500">Due: <span className="text-slate-300 font-mono">{t.order.dueDate}</span></span>
                      </div>
                      {t.reasoning && (
                        <p className="mt-3 rounded-xl bg-cyan-500/[0.06] border border-cyan-500/10 px-4 py-2.5 text-sm text-cyan-300/80">
                          <span className="font-medium text-cyan-400">AI Reasoning:</span> {t.reasoning}
                        </p>
                      )}
                      {t.status === "submitted_for_review" ? (
                        <div className="mt-4 flex items-center gap-3">
                          <button onClick={() => handleAccept(t)} className="inline-flex items-center gap-1.5 rounded-xl bg-emerald-500/15 px-4 py-2 text-sm font-medium text-emerald-400 ring-1 ring-emerald-500/20 hover:bg-emerald-500/25 transition-all duration-200" data-testid={`accept-transfer-${t.orderId}`}>
                            <Check size={15} /> Accept
                          </button>
                          {rejectingId !== t.id ? (
                            <button onClick={() => handleRejectClick(t.id)} className="inline-flex items-center gap-1.5 rounded-xl bg-red-500/15 px-4 py-2 text-sm font-medium text-red-400 ring-1 ring-red-500/20 hover:bg-red-500/25 transition-all duration-200" data-testid={`reject-transfer-${t.orderId}`}>
                              <X size={15} /> Reject
                            </button>
                          ) : (
                            <div className="flex flex-1 items-center gap-2">
                              <textarea value={rejectReason} onChange={(e) => setRejectReason(e.target.value)} placeholder="Reason (optional)" className="flex-1 rounded-xl border border-white/[0.08] bg-slate-800/80 px-3 py-2 text-sm text-slate-200 placeholder-slate-500 focus:border-red-500/30 focus:outline-none" rows={1} data-testid={`reject-reason-${t.orderId}`} />
                              <button onClick={() => handleRejectConfirm(t)} className="rounded-xl bg-red-500/15 px-3 py-2 text-sm font-medium text-red-400 hover:bg-red-500/25 transition-all" data-testid={`confirm-reject-${t.orderId}`}>Confirm</button>
                              <button onClick={handleRejectCancel} className="rounded-xl bg-white/[0.04] px-3 py-2 text-sm text-slate-400 hover:bg-white/[0.08] transition-all">Cancel</button>
                            </div>
                          )}
                        </div>
                      ) : (
                        <div className="mt-4 flex items-center gap-2">
                          <span className={`rounded-full px-2.5 py-0.5 text-[11px] font-medium ${statusStyles[t.status]}`}>{statusLabels[t.status]}</span>
                          {t.declineReason && <span className="text-sm text-red-400/70">Reason: {t.declineReason}</span>}
                        </div>
                      )}
                    </div>
                  ))}
                </div>
              )}
            </div>
          )}

          {/* Outgoing */}
          {activeTab === "outgoing" && (
            <div data-testid="outgoing-transfers">
              <p className="mb-4 text-sm text-slate-500">Orders submitted for transfer from your plant</p>
              {outgoing.length === 0 ? (
                <div className="glass-card p-16 text-center">
                  <div className="mx-auto mb-4 flex h-14 w-14 items-center justify-center rounded-xl bg-slate-700/50">
                    <ArrowUpFromLine size={24} className="text-slate-500" />
                  </div>
                  <p className="text-sm font-medium text-slate-400">No outgoing transfers</p>
                  <p className="mt-1 text-xs text-slate-600">Orders submitted for transfer will appear here</p>
                </div>
              ) : (
                <div className="space-y-4">
                  {outgoing.map((t) => (
                    <div key={t.id} className="glass-card p-5" data-testid={`outgoing-transfer-card-${t.orderId}`}>
                      <div className="flex items-center justify-between">
                        <div className="flex items-center gap-3">
                          <span className="text-sm font-semibold text-cyan-400 font-mono">{t.orderId}</span>
                          <span className={`rounded-full px-2.5 py-0.5 text-[11px] font-medium ${statusStyles[t.status]}`} data-testid={`transfer-status-${t.orderId}`}>{statusLabels[t.status]}</span>
                        </div>
                        <span className="text-xs text-slate-600">{new Date(t.proposedAt).toLocaleString()}</span>
                      </div>
                      <div className="mt-3 grid grid-cols-2 gap-3 text-sm sm:grid-cols-3">
                        <span className="text-slate-500">Product: <span className="text-slate-300">{t.order.productFamily}</span></span>
                        <span className="text-slate-500">Customer: <span className="text-slate-300">{t.order.customerName}</span></span>
                        <span className="text-slate-500">Value: <span className="text-slate-300">${t.order.orderValue.toLocaleString()}</span></span>
                      </div>
                      {t.reasoning && <p className="mt-3 text-sm text-slate-500">{t.reasoning}</p>}
                      {t.declineReason && (
                        <div className="mt-2 rounded-xl bg-red-500/[0.06] border border-red-500/10 px-4 py-2.5 text-sm text-red-400/80">
                          Decline reason: {t.declineReason}
                        </div>
                      )}
                    </div>
                  ))}
                </div>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

function TierBadge({ tier }: { tier: string }) {
  const s: Record<string, string> = { Tier1: "bg-emerald-500/10 text-emerald-400", Tier2: "bg-cyan-500/10 text-cyan-400", Tier3: "bg-slate-500/10 text-slate-400" };
  return <span className={`inline-flex rounded-full px-2.5 py-0.5 text-[11px] font-medium ${s[tier] ?? "bg-slate-500/10 text-slate-400"}`}>{tier}</span>;
}

function PriorityBadge({ priority }: { priority: string }) {
  const s: Record<string, string> = { P1: "bg-red-500/10 text-red-400 ring-1 ring-red-500/20", P2: "bg-amber-500/10 text-amber-400 ring-1 ring-amber-500/20", P3: "bg-slate-500/10 text-slate-400 ring-1 ring-slate-500/20" };
  return <span className={`inline-flex rounded-md px-2 py-0.5 text-[11px] font-bold tracking-wide ${s[priority] ?? "bg-slate-500/10 text-slate-400"}`}>{priority}</span>;
}
