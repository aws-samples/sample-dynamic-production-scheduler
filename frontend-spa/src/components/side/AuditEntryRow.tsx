import { useState } from "react";
import type { AuditEntry } from "@/types";
import { AgentBadge } from "@/components/chat/AgentBadge";

function relativeTime(iso: string): string {
  const diff = Date.now() - new Date(iso).getTime();
  const mins = Math.floor(diff / 60000);
  if (mins < 1) return "just now";
  if (mins < 60) return `${mins}m ago`;
  const hrs = Math.floor(mins / 60);
  if (hrs < 24) return `${hrs}h ago`;
  return `${Math.floor(hrs / 24)}d ago`;
}

interface AuditEntryRowProps {
  entry: AuditEntry;
}

export function AuditEntryRow({ entry }: AuditEntryRowProps) {
  const [expanded, setExpanded] = useState(false);

  return (
    <div
      className="cursor-pointer rounded px-2 py-1 text-xs hover:bg-gray-100/50"
      onClick={() => setExpanded(!expanded)}
    >
      <div className="flex items-center gap-2">
        <span className="text-gray-400 shrink-0">{relativeTime(entry.timestamp)}</span>
        <AgentBadge agentName={entry.agent} small />
        <span className="truncate text-gray-600">{entry.action}</span>
      </div>
      {expanded && (
        <p className="mt-1 whitespace-pre-wrap text-gray-400">{entry.details}</p>
      )}
    </div>
  );
}
