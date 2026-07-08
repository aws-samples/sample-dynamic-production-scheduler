import type { ReactNode } from "react";

interface SummaryCardProps {
  label: string;
  value: string | number;
  subtitle?: string;
  icon: ReactNode;
  iconBg?: string;
  valueColor?: string;
}

export function SummaryCard({
  label,
  value,
  subtitle,
  icon,
  iconBg = "bg-cyan-500/10",
  valueColor = "text-slate-100",
}: SummaryCardProps) {
  return (
    <div
      className="glass-card p-5 transition-all duration-300 hover:border-white/[0.1]"
      data-testid={`summary-card-${label.toLowerCase().replace(/\s+/g, "-")}`}
    >
      <div className="flex items-start gap-4">
        <div className={`flex h-11 w-11 shrink-0 items-center justify-center rounded-xl ${iconBg}`}>
          {icon}
        </div>
        <div className="min-w-0">
          <p className={`text-2xl font-bold tracking-tight ${valueColor}`}>{value}</p>
          <p className="text-sm text-slate-500">{label}</p>
          {subtitle && <p className="mt-0.5 text-xs text-slate-600">{subtitle}</p>}
        </div>
      </div>
    </div>
  );
}
