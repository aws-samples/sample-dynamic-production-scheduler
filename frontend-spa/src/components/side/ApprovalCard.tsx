import { useState, useEffect, useRef } from "react";
import { useStore } from "@/store";
import { send } from "@/lib/streaming";
import { AgentBadge } from "@/components/chat/AgentBadge";

export function ApprovalCard() {
  const pending = useStore((s) => s.sidePanel.pendingDecision);
  const sessionId = useStore((s) => s.session.sessionId);
  const [sending, setSending] = useState(false);
  const approveRef = useRef<HTMLButtonElement>(null);

  useEffect(() => {
    if (pending) {
      setSending(false);
      approveRef.current?.focus();
    }
  }, [pending?.orderId]);

  if (!pending) return null;

  const handleDecision = (decision: "approve" | "skip" | "reject") => {
    setSending(true);
    send({
      type: "order_decision",
      sessionId: sessionId ?? "",
      payload: { orderId: pending.orderId, decision, reason: null },
    });
  };

  const { order, recommendation, funnelResults, reasoning } = pending;

  return (
    <div className="space-y-3 p-4">
      <h3 className="text-xs font-semibold uppercase tracking-wider text-gray-500">
        Decision Required
      </h3>
      <div className="rounded-lg border border-gray-300 bg-white p-3 space-y-2">
        <div className="flex items-center justify-between">
          <span className="text-sm font-medium text-gray-900">{order.orderId}</span>
          <AgentBadge agentName="Constraint Matching Agent" small />
        </div>
        <div className="grid grid-cols-2 gap-x-4 gap-y-1 text-xs text-gray-500">
          <span>Product: <span className="text-gray-700">{order.productFamily}</span></span>
          <span>Customer: <span className="text-gray-700">{order.customerName}</span></span>
          <span>Priority: <span className="text-gray-700">{order.priority ?? "—"}</span></span>
          <span>Value: <span className="text-gray-700">${order.orderValue.toLocaleString()}</span></span>
          <span>Due: <span className="text-gray-700">{order.dueDate}</span></span>
          <span>Qty: <span className="text-gray-700">{order.quantity}</span></span>
        </div>
        <div className="space-y-1">
          <p className="text-xs font-medium text-gray-500">Funnel Results</p>
          {funnelResults.map((f) => (
            <div key={f.layer} className="flex items-center gap-2 text-xs">
              <span className={`h-2 w-2 rounded-full ${f.passed ? "bg-green-500" : "bg-red-500"}`} />
              <span className="text-gray-600">L{f.layer} {f.name}</span>
              <span className="text-gray-400">{f.detail}</span>
            </div>
          ))}
        </div>

        <div className="text-xs">
          <p className="text-gray-500">
            Recommendation: <span className="text-gray-700">{recommendation.replace(/_/g, " ")}</span>
          </p>
          <p className="mt-1 text-gray-400">{reasoning}</p>
        </div>

        <div className="flex gap-2 pt-1">
          <button
            ref={approveRef}
            data-testid="approval-card-approve-btn"
            aria-label={`Approve order ${order.orderId}`}
            className="min-h-11 flex-1 rounded-lg bg-green-700 px-3 py-2 text-sm font-medium text-white hover:bg-green-600 disabled:opacity-40"
            disabled={sending}
            onClick={() => handleDecision("approve")}
          >
            {sending ? "Sending..." : "Approve"}
          </button>
          <button
            data-testid="approval-card-skip-btn"
            aria-label={`Skip order ${order.orderId}`}
            className="min-h-11 flex-1 rounded-lg bg-yellow-700 px-3 py-2 text-sm font-medium text-white hover:bg-yellow-600 disabled:opacity-40"
            disabled={sending}
            onClick={() => handleDecision("skip")}
          >
            Skip
          </button>
          <button
            data-testid="approval-card-reject-btn"
            aria-label={`Reject order ${order.orderId}`}
            className="min-h-11 flex-1 rounded-lg bg-red-700 px-3 py-2 text-sm font-medium text-white hover:bg-red-600 disabled:opacity-40"
            disabled={sending}
            onClick={() => handleDecision("reject")}
          >
            Reject
          </button>
        </div>
      </div>
    </div>
  );
}
