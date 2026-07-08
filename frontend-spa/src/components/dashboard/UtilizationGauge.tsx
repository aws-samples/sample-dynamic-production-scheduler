interface UtilizationGaugeProps {
  label: string;
  value: number;
  subtitle?: string;
}

function getColor(v: number) {
  if (v > 85) return { ring: "#ef4444", text: "text-red-400" };
  if (v > 70) return { ring: "#f59e0b", text: "text-amber-400" };
  return { ring: "#06b6d4", text: "text-cyan-400" };
}

export function UtilizationGauge({ label, value, subtitle }: UtilizationGaugeProps) {
  const clamped = Math.min(100, Math.max(0, value));
  const c = getColor(clamped);
  const r = 42;
  const circ = 2 * Math.PI * r;
  const offset = circ - (clamped / 100) * circ;

  return (
    <div
      className="glass-card flex flex-col items-center p-5 transition-all duration-300 hover:border-white/[0.1]"
      data-testid={`gauge-${label.toLowerCase().replace(/\s+/g, "-")}`}
      role="meter"
      aria-valuenow={clamped}
      aria-valuemin={0}
      aria-valuemax={100}
      aria-label={`${label}: ${clamped}%`}
    >
      <div className="relative">
        <svg width="110" height="110" viewBox="0 0 110 110" className="rotate-[-90deg]">
          <circle cx="55" cy="55" r={r} fill="none" strokeWidth="7" stroke="rgba(148,163,184,0.1)" />
          <circle
            cx="55" cy="55" r={r} fill="none" strokeWidth="7"
            stroke={c.ring}
            strokeDasharray={circ}
            strokeDashoffset={offset}
            strokeLinecap="round"
            className="transition-all duration-700"
            style={{ filter: `drop-shadow(0 0 6px ${c.ring}40)` }}
          />
        </svg>
        <div className="absolute inset-0 flex items-center justify-center">
          <span className={`text-xl font-bold ${c.text}`}>{clamped}%</span>
        </div>
      </div>
      <p className="mt-3 text-sm font-semibold text-slate-200">{label}</p>
      {subtitle && <p className="text-[11px] text-slate-500">{subtitle}</p>}
    </div>
  );
}
