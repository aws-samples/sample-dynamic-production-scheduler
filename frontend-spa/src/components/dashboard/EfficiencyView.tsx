import { useStore } from "@/store";
import { SummaryCard } from "./SummaryCard";
import { UtilizationGauge } from "./UtilizationGauge";
import { Gauge, Users, Boxes } from "lucide-react";

export function EfficiencyView() {
  const facilityData = useStore((s) => s.facilityData);

  if (!facilityData) {
    return (
      <div data-testid="efficiency-view" className="flex items-center justify-center py-20">
        <p className="text-sm text-slate-500">Loading facility data...</p>
      </div>
    );
  }

  const { machines, workforce, materials } = facilityData;
  const avgUtil = machines.length > 0
    ? Math.round(machines.reduce((s, m) => s + m.normalUtilizationPct, 0) / machines.length)
    : 0;
  const workforcePct = workforce.totalOperators > 0
    ? Math.round((workforce.allocated / workforce.totalOperators) * 100)
    : 0;
  const totalMaterial = materials.reduce((s, m) => s + m.currentTons, 0);

  return (
    <div data-testid="efficiency-view" className="space-y-8">
      {/* Summary cards */}
      <div className="grid grid-cols-3 gap-4">
        <SummaryCard
          label="Avg Utilization"
          value={`${avgUtil}%`}
          icon={<Gauge size={20} className={avgUtil > 85 ? "text-red-400" : avgUtil > 70 ? "text-amber-400" : "text-cyan-400"} />}
          iconBg={avgUtil > 85 ? "bg-red-500/10" : avgUtil > 70 ? "bg-amber-500/10" : "bg-cyan-500/10"}
          valueColor={avgUtil > 85 ? "text-red-400" : avgUtil > 70 ? "text-amber-400" : "text-cyan-400"}
        />
        <SummaryCard
          label="Workforce Allocation"
          value={`${workforcePct}%`}
          subtitle={`${workforce.allocated} of ${workforce.totalOperators} operators`}
          icon={<Users size={20} className="text-violet-400" />}
          iconBg="bg-violet-500/10"
        />
        <SummaryCard
          label="Material Stock"
          value={`${totalMaterial.toLocaleString()}t`}
          icon={<Boxes size={20} className={totalMaterial < 500 ? "text-amber-400" : "text-emerald-400"} />}
          iconBg={totalMaterial < 500 ? "bg-amber-500/10" : "bg-emerald-500/10"}
        />
      </div>

      {/* Machine utilization */}
      <div>
        <h3 className="mb-4 text-sm font-semibold text-slate-300 uppercase tracking-wider">Machine Utilization</h3>
        <div className="grid grid-cols-2 gap-4 lg:grid-cols-4">
          {machines.map((m) => (
            <UtilizationGauge
              key={m.machineType}
              label={m.machineType}
              value={m.normalUtilizationPct}
              subtitle={`2-shift base · OT: +${m.overtimeAvailablePct}% · Wknd: +${m.weekendAvailablePct}%`}
            />
          ))}
        </div>
      </div>

      {/* Workforce */}
      <div>
        <h3 className="mb-4 text-sm font-semibold text-slate-300 uppercase tracking-wider">Workforce Allocation</h3>
        <div className="glass-card p-5" data-testid="workforce-chart">
          <div className="mb-3 flex justify-between text-sm">
            <span className="text-slate-400">Allocated: <span className="font-semibold text-slate-200">{workforce.allocated}</span></span>
            <span className="text-slate-400">Surplus: <span className="font-semibold text-emerald-400">{workforce.surplus}</span></span>
          </div>
          <div className="h-3 overflow-hidden rounded-full bg-slate-700/50">
            <div
              className={`h-full rounded-full transition-all duration-700 ${
                workforcePct > 90 ? "bg-red-500" : workforcePct > 75 ? "bg-amber-500" : "bg-cyan-500"
              }`}
              style={{ width: `${workforcePct}%`, boxShadow: `0 0 12px ${workforcePct > 90 ? "rgba(239,68,68,0.3)" : workforcePct > 75 ? "rgba(245,158,11,0.3)" : "rgba(6,182,212,0.3)"}` }}
            />
          </div>
          <p className="mt-2 text-right text-xs text-slate-600">{workforce.totalOperators} total operators</p>
        </div>
      </div>

      {/* Materials */}
      <div>
        <div className="mb-4 flex items-center justify-between">
          <h3 className="text-sm font-semibold text-slate-300 uppercase tracking-wider">Material Inventory</h3>
          <div className="flex items-center gap-4 text-[11px] text-slate-500">
            <span className="flex items-center gap-1.5"><span className="inline-block h-2 w-2 rounded-full bg-emerald-500 shadow-sm shadow-emerald-500/50" /> &gt;30% surplus</span>
            <span className="flex items-center gap-1.5"><span className="inline-block h-2 w-2 rounded-full bg-amber-500 shadow-sm shadow-amber-500/50" /> 15–30%</span>
            <span className="flex items-center gap-1.5"><span className="inline-block h-2 w-2 rounded-full bg-red-500 shadow-sm shadow-red-500/50" /> &lt;15%</span>
          </div>
        </div>
        <div className="grid gap-4 lg:grid-cols-3" data-testid="material-levels">
          {materials.map((m) => {
            const pct = m.currentTons > 0 ? Math.round((m.committedTons / m.currentTons) * 100) : 0;
            const surplusPct = m.currentTons > 0 ? Math.round((m.surplusTons / m.currentTons) * 100) : 0;
            const barColor = surplusPct < 15 ? "bg-red-500" : surplusPct < 30 ? "bg-amber-500" : "bg-emerald-500";
            const badgeColor = surplusPct < 15 ? "text-red-400 bg-red-500/10" : surplusPct < 30 ? "text-amber-400 bg-amber-500/10" : "text-emerald-400 bg-emerald-500/10";
            const glowColor = surplusPct < 15 ? "rgba(239,68,68,0.2)" : surplusPct < 30 ? "rgba(245,158,11,0.2)" : "rgba(16,185,129,0.2)";
            return (
              <div key={m.materialType} className="glass-card p-5 transition-all duration-300 hover:border-white/[0.1]">
                <div className="mb-3 flex items-center justify-between">
                  <span className="text-sm font-semibold text-slate-200">{m.materialType}</span>
                  <span className={`rounded-full px-2.5 py-0.5 text-[11px] font-medium ${badgeColor}`}>
                    {m.surplusTons}t surplus
                  </span>
                </div>
                <div className="h-2.5 overflow-hidden rounded-full bg-slate-700/50">
                  <div
                    className={`h-full rounded-full transition-all duration-700 ${barColor}`}
                    style={{ width: `${pct}%`, boxShadow: `0 0 10px ${glowColor}` }}
                  />
                </div>
                <div className="mt-2.5 flex justify-between text-[11px] text-slate-500">
                  <span>Committed: <span className="text-slate-400">{m.committedTons}t</span></span>
                  <span>Total: <span className="text-slate-400">{m.currentTons}t</span></span>
                </div>
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
}
