import { useStore } from "@/store";
import type { OrderDecision } from "@/types";

type Column = "approved" | "rejected" | "skipped";

const COLUMNS: { key: Column; label: string; color: string; bg: string }[] = [
  { key: "approved", label: "Approved", color: "text-emerald-700", bg: "bg-emerald-50" },
  { key: "rejected", label: "Rejected", color: "text-red-700", bg: "bg-red-50" },
  { key: "skipped", label: "Skipped", color: "text-amber-700", bg: "bg-amber-50" },
];

function OrderCard({ order }: { order: OrderDecision }) {
  return (
    <div className="rounded-lg border border-gray-200 bg-white p-2.5 shadow-sm">
      <p className="text-xs font-semibold font-mono text-gray-800">{order.orderId}</p>
      {order.reasoning && (
        <p className="text-[10px] text-gray-400 mt-0.5 truncate">{order.reasoning}</p>
      )}
    </div>
  );
}

export function KanbanBoard() {
  const orderHistory = useStore((s) => s.orderHistory);

  if (orderHistory.length === 0) return null;

  function ordersInColumn(col: Column): OrderDecision[] {
    if (col === "approved") return orderHistory.filter((o) => o.decision === "approve");
    if (col === "rejected") return orderHistory.filter((o) => o.decision === "reject");
    return orderHistory.filter((o) => o.decision === "skip");
  }

  return (
    <div className="flex gap-3 overflow-x-auto" data-testid="kanban-board">
      {COLUMNS.map((col) => {
        const orders = ordersInColumn(col.key);
        return (
          <div key={col.key} className={`flex w-44 shrink-0 flex-col rounded-lg ${col.bg} p-2`}>
            <div className="mb-2 flex items-center justify-between px-1">
              <span className={`text-xs font-semibold ${col.color}`}>{col.label}</span>
              <span className="rounded-full bg-white px-1.5 py-0.5 text-[10px] font-medium text-gray-500 shadow-sm">
                {orders.length}
              </span>
            </div>
            <div className="flex flex-col gap-1.5">
              {orders.map((o) => (
                <OrderCard key={o.orderId} order={o} />
              ))}
            </div>
          </div>
        );
      })}
    </div>
  );
}
