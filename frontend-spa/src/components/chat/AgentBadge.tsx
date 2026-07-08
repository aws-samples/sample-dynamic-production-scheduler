const AGENT_COLORS: Record<string, string> = {
  "Orchestrator Agent": "bg-cyan-500/15 text-cyan-400 border-cyan-500/40",
  "Impact Assessment Agent": "bg-amber-500/15 text-amber-400 border-amber-500/40",
  "Capacity & Optimization Agent": "bg-emerald-500/15 text-emerald-400 border-emerald-500/40",
  "Constraint Matching Agent": "bg-violet-500/15 text-violet-400 border-violet-500/40",
  System: "bg-red-500/15 text-red-400 border-red-500/40",
};

const DEFAULT_COLOR = "bg-white/[0.04] text-slate-400 border-white/[0.06]";

interface AgentBadgeProps {
  agentName: string;
  small?: boolean;
}

export function AgentBadge({ agentName, small }: AgentBadgeProps) {
  const color = AGENT_COLORS[agentName] ?? DEFAULT_COLOR;
  const size = small ? "text-[10px] px-1.5 py-0.5" : "text-xs px-2 py-0.5";

  return (
    <span className={`inline-block rounded-full border ${color} ${size} font-medium transition-all duration-200`}>
      {agentName}
    </span>
  );
}
