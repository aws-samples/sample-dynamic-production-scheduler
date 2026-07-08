import { BarChart3, ArrowRight, AlertTriangle, TrendingUp, Package } from "lucide-react";
import { SafeMarkdown } from "@/lib/markdown";
import type { UiPayload, UiPriorities, UiCapacity, UiOrder } from "@/types";

interface Round1ResultsProps {
  content: string;
  uiData?: UiPayload | null;
  onProceed?: () => void;
  proceeding: boolean;
  receivingPlant?: string;
}

/** Build priority display rows from structured UiPriorities */
function buildPriorities(p: UiPriorities | null | undefined) {
  if (!p) return [];
  const rows: { label: string; count: number; value: string; color: string }[] = [];
  if (p.P1 != null) rows.push({ label: "P1 Must Move", count: p.P1, value: p.P1Value ?? "", color: "bg-red-100 text-red-700" });
  if (p.P2 != null) rows.push({ label: "P2 Move if Capacity", count: p.P2, value: p.P2Value ?? "", color: "bg-amber-100 text-amber-700" });
  if (p.P3 != null) rows.push({ label: "P3 Defer", count: p.P3, value: p.P3Value ?? "", color: "bg-green-100 text-green-700" });
  return rows;
}

/** Build capacity dimension rows from structured UiCapacity (percentages → bar data) */
function buildCapacityDims(c: UiCapacity | null | undefined) {
  if (!c) return [];
  const dims: { label: string; used: number; available: number; unit: string; note: string }[] = [];
  if (c.rollingMill != null) {
    // Compute used/available hours from utilization % and surplus hours
    // surplus = total * (1 - pct/100), so total = surplus / (1 - pct/100)
    // used = total - surplus
    const pct = c.rollingMill;
    const surplus = c.rollingMillSurplusHrs ?? 0;
    let total = 0;
    let used = 0;
    if (pct < 100 && surplus > 0) {
      total = Math.round(surplus / (1 - pct / 100));
      used = total - Math.round(surplus);
    } else if (pct >= 100) {
      // Fully utilized — show as overbooked
      total = surplus > 0 ? Math.round(surplus / (1 - Math.min(pct, 99.9) / 100)) : 148;
      used = total;
    }
    dims.push({ label: "Rolling Mill", used, available: total, unit: "hrs", note: `${pct}% utilized` });
  }
  if (c.finishingLine != null) {
    const pct = c.finishingLine;
    const surplus = c.finishingLineSurplusHrs ?? 0;
    let total = 0;
    let used = 0;
    if (pct < 100 && surplus > 0) {
      total = Math.round(surplus / (1 - pct / 100));
      used = total - Math.round(surplus);
    } else if (pct >= 100) {
      total = surplus > 0 ? Math.round(surplus / (1 - Math.min(pct, 99.9) / 100)) : 152;
      used = total;
    }
    dims.push({ label: "Finishing Line", used, available: total, unit: "hrs", note: `${pct}% utilized` });
  }
  if (c.workforce != null) dims.push({ label: "Workforce", used: 0, available: 0, unit: "", note: `${c.workforce}% utilized` });
  if (c.rawMaterial != null) dims.push({ label: "Materials", used: 0, available: 0, unit: "", note: `${c.rawMaterial}% utilized` });
  return dims;
}

/** Map UiOrder[] to the display shape used by the order table */
function buildTopOrders(orders: UiOrder[] | null | undefined) {
  if (!orders || orders.length === 0) return [];
  return orders.slice(0, 5).map((o) => ({
    id: o.orderId,
    customer: o.customer ?? "",
    value: o.value ?? "",
    due: o.dueDate ?? "",
  }));
}

export function Round1ResultsCard({ content, uiData, onProceed, proceeding, receivingPlant }: Round1ResultsProps) {

  // If no structured uiData, fall back to raw markdown display
  if (!uiData) {
    return (
      <div className="space-y-4" data-testid="round1-results-card">
        <div className="rounded-xl border border-blue-200 bg-white shadow-sm overflow-hidden p-5">
          <div className="prose prose-sm prose-gray max-w-none">
            <SafeMarkdown content={content} />
          </div>
        </div>
        <button
          onClick={onProceed}
          disabled={proceeding}
          className="flex items-center gap-2 rounded-lg bg-blue-600 px-6 py-3 text-sm font-semibold text-white shadow-sm hover:bg-blue-500 disabled:opacity-40"
          data-testid="proceed-round2-btn"
        >
          {proceeding ? "Starting..." : "Proceed to Round 2 — Delay Optimization"}
          {!proceeding && <ArrowRight size={16} />}
        </button>
      </div>
    );
  }

  // Consume structured data from uiData
  const priorities = buildPriorities(uiData.priorities);
  const capacityDims = buildCapacityDims(uiData.capacity);
  const topOrders = buildTopOrders(uiData.orders);
  const totalOrders = uiData.totalOrders ?? topOrders.length;
  const totalValue = uiData.totalValue ?? "";
  const bottleneck = uiData.bottleneck ?? "Unknown";
  const receivingPlantName = receivingPlant || "Receiving Plant";

  return (
    <div className="space-y-4" data-testid="round1-results-card">
      {/* Summary header */}
      <div className="rounded-xl border border-blue-200 bg-white shadow-sm overflow-hidden">
        <div className="bg-blue-50 px-5 py-3 border-b border-blue-100">
          <div className="flex items-center gap-2">
            <BarChart3 size={16} className="text-blue-600" />
            <h3 className="text-sm font-semibold text-gray-900">Round 1 — Intelligence Gathering Complete</h3>
          </div>
        </div>

        <div className="p-5 space-y-6">
          {/* Overview stats */}
          <div>
            <p className="text-xs text-gray-500 mb-2">High-level snapshot of the disrupted plant's affected orders and the receiving plant's primary constraint.</p>
            <div className="grid grid-cols-3 gap-3">
              <StatCard icon={Package} label="Orders Affected" value={String(totalOrders)} color="text-blue-600" />
              <StatCard icon={TrendingUp} label="Portfolio Value" value={totalValue ? `${totalValue}` : "N/A"} color="text-emerald-600" />
              <StatCard icon={AlertTriangle} label="Bottleneck" value={bottleneck} color="text-red-600" tooltip={bottleneck} />
            </div>
          </div>

          {/* Priority distribution */}
          {priorities.length > 0 && (
            <div>
              <h4 className="text-xs font-medium text-gray-500 uppercase tracking-wide mb-1">Disruption Impact Priority</h4>
              <p className="text-xs text-gray-500 mb-2">AI-assessed urgency based on due dates, customer tier, and order value — may differ from original order priority.</p>
              <div className="grid grid-cols-3 gap-2">
                {priorities.map((p) => (
                  <div key={p.label} className={`rounded-lg p-3 ${p.color} bg-opacity-50`}>
                    <div className="text-lg font-bold">{p.count}</div>
                    <div className="text-xs font-medium">{p.label}</div>
                    <div className="text-xs opacity-75">{p.value}</div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Capacity gauges */}
          {capacityDims.length > 0 && (
            <div>
              <h4 className="text-xs font-medium text-gray-500 uppercase tracking-wide mb-1">{receivingPlantName} Plant Capacity</h4>
              <p className="text-xs text-gray-500 mb-3">
                Bars show demand vs. available hours. Overbooked dimensions require mitigation (delays, overtime) before Florida orders can be absorbed.
              </p>
              <div className="space-y-2">
                {capacityDims.map((dim) => (
                  <CapacityBar key={dim.label} label={dim.label} used={dim.used} available={dim.available} unit={dim.unit} note={dim.note} />
                ))}
              </div>
            </div>
          )}

          {/* Top orders */}
          {topOrders.length > 0 && (
            <div>
              <h4 className="text-xs font-medium text-gray-500 uppercase tracking-wide mb-1">Top Priority Orders</h4>
              <p className="text-xs text-gray-500 mb-2">Highest-urgency orders recommended for immediate transfer to the receiving plant.</p>
              <div className="rounded-lg border border-gray-200 overflow-hidden">
                <table className="w-full text-xs">
                  <thead className="bg-gray-50">
                    <tr>
                      <th className="px-3 py-2 text-left font-medium text-gray-500">Order</th>
                      {topOrders[0]?.customer && <th className="px-3 py-2 text-left font-medium text-gray-500">Customer</th>}
                      {topOrders[0]?.value && <th className="px-3 py-2 text-right font-medium text-gray-500">Value</th>}
                      {topOrders[0]?.due && <th className="px-3 py-2 text-right font-medium text-gray-500">Due</th>}
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-gray-100">
                    {topOrders.map((o) => (
                      <tr key={o.id}>
                        <td className="px-3 py-2 font-mono font-medium text-gray-900">{o.id}</td>
                        {o.customer && <td className="px-3 py-2 text-gray-600">{o.customer}</td>}
                        {o.value && <td className="px-3 py-2 text-right text-gray-600">{o.value}</td>}
                        {o.due && <td className="px-3 py-2 text-right text-gray-500">{o.due}</td>}
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          )}
        </div>
      </div>

      <button
        onClick={onProceed}
        disabled={proceeding}
        className="flex items-center gap-2 rounded-lg bg-blue-600 px-6 py-3 text-sm font-semibold text-white shadow-sm hover:bg-blue-500 disabled:opacity-40"
        data-testid="proceed-round2-btn"
      >
        {proceeding ? "Starting..." : "Proceed to Round 2 — Delay Optimization"}
        {!proceeding && <ArrowRight size={16} />}
      </button>
    </div>
  );
}

function StatCard({ icon: Icon, label, value, color, tooltip }: { icon: typeof Package; label: string; value: string; color: string; tooltip?: string }) {
  // For long values (like bottleneck), show a short version with hover tooltip
  const isLong = value.length > 30;
  const shortValue = isLong ? value.split(/\s*[-—–]\s*/)[0]?.trim() || value.slice(0, 25) + "…" : value;

  return (
    <div className="rounded-lg border border-gray-200 bg-gray-50 p-3 group relative" title={tooltip || (isLong ? value : undefined)}>
      <div className="flex items-center gap-1.5 mb-1">
        <Icon size={14} className={color} />
        <span className="text-[10px] font-medium uppercase tracking-wide text-gray-400">{label}</span>
      </div>
      <p className="text-sm font-semibold text-gray-800 truncate">{shortValue}</p>
      {isLong && (
        <div className="absolute left-0 right-0 top-full z-20 mt-1 hidden group-hover:block">
          <div className="rounded-lg border border-gray-200 bg-white p-3 shadow-lg text-xs text-gray-700 leading-relaxed max-h-40 overflow-y-auto">
            {value}
          </div>
        </div>
      )}
    </div>
  );
}

function CapacityBar({ label, used, available, unit, note }: { label: string; used: number; available: number; unit: string; note: string }) {
  // Text-only row (workforce, materials)
  if (available === 0 && used === 0) {
    return (
      <div className="flex items-center gap-3">
        <span className="w-28 text-xs text-gray-600 shrink-0">{label}</span>
        <span className="text-xs text-gray-500">{note}</span>
      </div>
    );
  }

  const overbooked = used > available;
  const fillPct = Math.min((used / available) * 100, 100);
  const barColor = overbooked ? "bg-red-500" : fillPct > 85 ? "bg-amber-500" : "bg-emerald-500";

  return (
    <div className="flex items-center gap-3">
      <span className="w-28 text-xs text-gray-600 shrink-0">{label}</span>
      <div className="flex-1 h-3 bg-gray-200 rounded-full overflow-hidden relative">
        <div className={`h-full rounded-full ${barColor}`} style={{ width: `${fillPct}%` }} />
      </div>
      <span className={`text-xs font-medium w-28 text-right ${overbooked ? "text-red-600" : "text-gray-600"}`}>
        {used}/{available} {unit}
        {overbooked && <span className="ml-1 text-[10px]">⚠️</span>}
      </span>
    </div>
  );
}
