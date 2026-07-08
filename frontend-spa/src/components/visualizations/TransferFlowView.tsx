import { useStore } from "@/store";

export function TransferFlowView() {
  const orderHistory = useStore((s) => s.orderHistory);
  const capacity = useStore((s) => s.capacity);

  const approved = orderHistory.filter((d) => d.decision === "approve");

  if (approved.length === 0) {
    return (
      <div className="p-4 text-sm text-gray-400">
        No approved transfers yet. Approve orders to see the transfer flow.
      </div>
    );
  }

  return (
    <div className="space-y-3 p-3">
      <h3 className="text-xs font-medium uppercase tracking-wider text-gray-500">
        Transfer Flow
      </h3>
      <div className="flex items-center justify-between rounded bg-gray-100/50 px-3 py-2">
        <div className="text-center">
          <div className="text-xs text-gray-500">Disrupted Plant</div>
          <div className="text-lg font-bold text-red-500">{approved.length}</div>
          <div className="text-xs text-gray-400">orders out</div>
        </div>
        <div className="flex-1 flex items-center justify-center px-2">
          <div className="h-px flex-1 bg-zinc-600" />
          <div className="mx-2 text-xs text-gray-500">transfer</div>
          <div className="h-px flex-1 bg-zinc-600" />
        </div>
        <div className="text-center">
          <div className="text-xs text-gray-500">Receiving Plant</div>
          <div className="text-lg font-bold text-emerald-400">{approved.length}</div>
          <div className="text-xs text-gray-400">orders in</div>
        </div>
      </div>
      {capacity && (
        <div className="text-xs text-gray-500">
          Remaining capacity: Rolling Mill{" "}
          {(capacity.rollingMill.available - capacity.rollingMill.used).toFixed(1)}
          {capacity.rollingMill.unit}, Finishing Line{" "}
          {(capacity.finishingLine.available - capacity.finishingLine.used).toFixed(1)}
          {capacity.finishingLine.unit}
        </div>
      )}
      <div className="space-y-1 max-h-40 overflow-y-auto">
        {approved.map((d, i) => (
          <div
            key={`${d.orderId}-${i}`}
            className="flex items-center justify-between rounded bg-gray-100/30 px-2 py-1 text-xs"
          >
            <span className="font-mono text-gray-600">{d.orderId}</span>
            <span className="text-emerald-400">Transferred</span>
          </div>
        ))}
      </div>
    </div>
  );
}
