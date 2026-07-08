import { useStore } from "@/store";
import { Activity, CheckCircle, AlertCircle, Clock } from "lucide-react";

const STATUS_CONFIG: Record<string, { icon: typeof Activity; color: string; label: string }> = {
  idle: { icon: Clock, color: "text-gray-400", label: "Idle" },
  running: { icon: Activity, color: "text-blue-600", label: "Running" },
  complete: { icon: CheckCircle, color: "text-emerald-400", label: "Complete" },
  error: { icon: AlertCircle, color: "text-red-500", label: "Error" },
};

export function SubAgentStatus() {
  const subAgents = useStore((s) => s.subAgents);

  if (subAgents.length === 0) {
    return (
      <div className="p-4 text-sm text-slate-400">
        No sub-agents active yet. Start a disruption analysis to see agent status.
      </div>
    );
  }

  return (
    <div className="space-y-2 p-3">
      <h3 className="text-xs font-medium uppercase tracking-wider text-slate-400">
        Sub-Agent Status
      </h3>
      {subAgents.map((agent) => {
        const cfg = STATUS_CONFIG[agent.status] ?? STATUS_CONFIG["idle"];
        if (!cfg) return null;
        const Icon = cfg.icon;
        return (
          <div
            key={agent.name}
            className="flex items-center gap-2 rounded-lg bg-slate-750 border border-slate-700 px-3 py-2"
            data-testid={`agent-status-${agent.name.toLowerCase().replace(/\s+/g, "-")}`}
          >
            <Icon size={14} className={cfg.color} />
            <div className="flex-1 min-w-0">
              <div className="text-sm text-slate-200 truncate">{agent.name}</div>
              {agent.summary && (
                <div className="text-xs text-slate-400 truncate">{agent.summary}</div>
              )}
            </div>
            <span className={`text-xs ${cfg.color}`}>{cfg.label}</span>
          </div>
        );
      })}
    </div>
  );
}
