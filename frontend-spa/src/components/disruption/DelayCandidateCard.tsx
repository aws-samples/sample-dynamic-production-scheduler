import { useState } from "react";
import { useStore } from "@/store";
import { CheckCircle, XCircle, SkipForward, Clock, Package, AlertTriangle, TrendingUp } from "lucide-react";

interface DelayCandidateCardProps {
  ui: import("@/types").UiPayload | Record<string, unknown>;
  candidateNum?: number;
  totalCandidates?: number;
  /** When provided, the parent handles the decision — card skips internal sendMessage/store logic */
  onDecision?: (decision: string) => void | Promise<void>;
}

export function DelayCandidateCard({ ui, candidateNum, totalCandidates, onDecision }: DelayCandidateCardProps) {
  const approval = ui.approvalRequest as Record<string, unknown> | undefined;
  if (!approval) return null;

  const orderId = String(approval.orderId || "");
  const existingDecision = useStore((s) => s.orderHistory.find((o) => o.orderId === orderId));

  const product = String(approval.product || "");
  const customer = String(approval.customer || "");
  const value = String(approval.value || "");
  const recommendation = String(approval.recommendation || "");
  const reasoning = String(approval.reasoning || "");
  const funnelResults = (approval.funnelResults || []) as Array<{ layer: number; name: string; passed: boolean; detail: string }>;

  const [decision, setDecision] = useState<string | null>(null);
  const [submitted, setSubmitted] = useState(!!existingDecision);
  const [sending, setSending] = useState(false);

  const orders = (ui.orders || []) as Array<Record<string, string>>;
  const orderData = orders.find((o) => o.orderId === orderId) || {};
  const dueDate = orderData.dueDate || "";
  const slack = orderData.slack || "";
  const rmHrs = orderData.rmHrs || "";
  const flHrs = orderData.flHrs || "";
  const risk = orderData.risk || "";

  const options = (approval.options || []) as Array<Record<string, string>>;

  if (submitted || existingDecision) {
    const dec = existingDecision?.decision || decision || "";
    const isApproved = /approve/i.test(dec);
    const isSkipped = /skip/i.test(dec);
    const borderColor = isApproved ? "border-emerald-200 bg-emerald-50" : isSkipped ? "border-gray-200 bg-gray-50" : "border-red-200 bg-red-50";
    const textColor = isApproved ? "text-emerald-700" : isSkipped ? "text-gray-600" : "text-red-700";
    const iconColor = isApproved ? "text-emerald-600" : isSkipped ? "text-gray-500" : "text-red-600";
    const statusText = isApproved ? "APPROVED" : isSkipped ? "SKIPPED" : "REJECTED";
    return (
      <div className={`rounded-xl border p-4 ${borderColor}`}>
        <div className="flex items-center gap-2">
          {isApproved ? <CheckCircle size={16} className={iconColor} /> : isSkipped ? <SkipForward size={16} className={iconColor} /> : <XCircle size={16} className={iconColor} />}
          <span className="text-sm font-medium font-mono">{orderId}</span>
          <span className={`text-xs font-medium ${textColor}`}>{statusText}</span>
        </div>
      </div>
    );
  }

  return (
    <div className="rounded-xl border border-amber-200 bg-white shadow-sm overflow-hidden" data-testid={`delay-card-${orderId}`}>
      <div className="bg-amber-50 px-5 py-3 border-b border-amber-100">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Clock size={16} className="text-amber-600" />
            <span className="text-sm font-semibold text-gray-900">Candidate{candidateNum ? ` ${candidateNum}` : ""}{totalCandidates ? ` of ${totalCandidates}` : ""}</span>
          </div>
          <span className="font-mono text-sm font-bold text-amber-700">{orderId}</span>
        </div>
      </div>

      <div className="p-5 space-y-4">
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
          {product && <DetailCell icon={Package} label="Product" value={product} />}
          {(customer || orderData.customer) && <DetailCell icon={null} label="Customer" value={customer || orderData.customer || ""} />}
          {(value || orderData.value) && <DetailCell icon={TrendingUp} label="Value" value={value || orderData.value || ""} />}
          {dueDate && <DetailCell icon={null} label="Due Date" value={dueDate} />}
          {slack && <DetailCell icon={null} label="Slack" value={slack} />}
          {risk && <DetailCell icon={AlertTriangle} label="Risk" value={risk} />}
        </div>

        {(rmHrs || flHrs) && (
          <div>
            <p className="text-[10px] font-medium text-gray-400 uppercase tracking-wide mb-1">Capacity Freed</p>
            <div className="flex gap-3">
              {rmHrs && (
                <div className="rounded-lg bg-blue-50 px-3 py-1.5">
                  <span className="text-xs font-semibold text-blue-700">{rmHrs} hrs</span>
                  <span className="text-[10px] text-blue-500 ml-1">Rolling Mill</span>
                </div>
              )}
              {flHrs && (
                <div className="rounded-lg bg-purple-50 px-3 py-1.5">
                  <span className="text-xs font-semibold text-purple-700">{flHrs} hrs</span>
                  <span className="text-[10px] text-purple-500 ml-1">Finishing Line</span>
                </div>
              )}
            </div>
          </div>
        )}

        {funnelResults.length > 0 && (
          <div>
            <p className="text-[10px] font-medium text-gray-400 uppercase tracking-wide mb-1.5">Constraint Funnel</p>
            <div className="space-y-1">
              {funnelResults.map((f) => (
                <div key={f.layer} className="flex items-start gap-2 text-xs">
                  <span className={`mt-0.5 flex-shrink-0 ${f.passed ? "text-emerald-500" : "text-red-500"}`}>
                    {f.passed ? "✓" : "✗"}
                  </span>
                  <span className="font-medium text-gray-700 w-24 flex-shrink-0">L{f.layer} {f.name}</span>
                  <span className="text-gray-500">{f.detail}</span>
                </div>
              ))}
            </div>
          </div>
        )}

        {(recommendation || reasoning) && (
          <div className="rounded-lg bg-blue-50 px-3 py-2 border border-blue-100">
            <p className="text-[10px] font-medium text-blue-500 uppercase tracking-wide mb-0.5">AI Recommendation</p>
            <p className="text-xs font-semibold text-blue-800">{recommendation}</p>
            {reasoning && reasoning !== recommendation && (
              <p className="text-xs text-blue-700 mt-1">{reasoning}</p>
            )}
          </div>
        )}

        <div className="flex items-center gap-3 pt-2 border-t border-gray-100">
          {options.map((opt) => {
            const key = opt.key || opt.label?.toLowerCase() || "";
            const isApprove = /approve/i.test(key);
            const isSkip = /skip/i.test(key);
            const colorClass = isApprove
              ? "border border-emerald-300 bg-white text-emerald-700 hover:bg-emerald-600 hover:text-white"
              : isSkip
                ? "border border-gray-300 bg-white text-gray-600 hover:bg-gray-500 hover:text-white"
                : "border border-red-300 bg-white text-red-700 hover:bg-red-600 hover:text-white";
            const label = opt.label || (isApprove ? "✓ Approve" : isSkip ? "⏭ Skip" : "✗ Reject");
            return (
              <button
                key={key}
                disabled={sending}
                onClick={async () => {
                  setDecision(key);
                  setSending(true);
                  if (onDecision) {
                    await onDecision(key);
                  } else {
                    const store = useStore.getState();
                    const mapped = isApprove ? "approve" as const : "reject" as const;
                    store.addOrderDecision({ orderId, decision: mapped, agentName: "User", timestamp: new Date().toISOString(), reasoning: key });
                    // Decision is frontend-only — no message to orchestrator
                  }
                  setSubmitted(true);
                  setSending(false);
                }}
                className={`flex-1 rounded-lg py-2.5 text-sm font-semibold transition-colors ${colorClass} disabled:opacity-40`}
              >
                {sending && decision === key ? "Submitting..." : label}
                {opt.hint && <span className="block text-[10px] font-normal opacity-75 mt-0.5">{opt.hint}</span>}
              </button>
            );
          })}
        </div>
      </div>
    </div>
  );
}

function DetailCell({ icon: Icon, label, value }: { icon: typeof Package | null; label: string; value: string }) {
  return (
    <div className="rounded-lg bg-gray-50 p-2">
      <div className="flex items-center gap-1 mb-0.5">
        {Icon && <Icon size={10} className="text-gray-400" />}
        <span className="text-[10px] font-medium text-gray-400 uppercase tracking-wide">{label}</span>
      </div>
      <p className="text-xs font-medium text-gray-800 truncate">{value}</p>
    </div>
  );
}
