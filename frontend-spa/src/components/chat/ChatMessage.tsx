import { useState, useMemo } from "react";
import type { ChatMessage as ChatMessageType } from "@/types";
import { SafeMarkdown } from "@/lib/markdown";
import { AgentBadge } from "./AgentBadge";
import { StructuredDataSummary } from "./StructuredDataSummary";
import { ExpandableReasoning } from "./ExpandableReasoning";
import { InlineApprovalButtons } from "./InlineApprovalButtons";
import { FormattedAgentResponse } from "./FormattedAgentResponse";
import { hasApprovalRequests, extractApprovalRequests } from "@/lib/responseParser";
import { ChevronDown, ChevronUp } from "lucide-react";

const COLLAPSE_THRESHOLD = 1200;

interface ChatMessageProps {
  message: ChatMessageType;
  showBadge: boolean;
}

export function ChatMessage({ message, showBadge }: ChatMessageProps) {
  const isUser = message.role === "user";
  const [expanded, setExpanded] = useState(false);

  // Detect approval requests in assistant messages (only when done streaming)
  const approvalOrders = useMemo(() => {
    if (isUser || message.isStreaming) return [];
    if (!hasApprovalRequests(message.content)) return [];
    return extractApprovalRequests(message.content);
  }, [isUser, message.isStreaming, message.content]);

  const isLong =
    !isUser && !message.isStreaming && message.content.length > COLLAPSE_THRESHOLD;

  const displayContent =
    isLong && !expanded
      ? message.content.slice(0, COLLAPSE_THRESHOLD) + "..."
      : message.content;

  return (
    <div
      className={`flex flex-col gap-2 ${isUser ? "items-end" : "items-start"}`}
    >
      {showBadge && message.agentName && (
        <AgentBadge agentName={message.agentName} />
      )}
      <div
        className={`max-w-[85%] rounded-2xl px-4 py-3 text-sm shadow-lg ${
          isUser
            ? "bg-slate-700 text-slate-100"
            : "bg-blue-900/80 text-slate-100 border border-blue-700/50"
        }`}
      >
        {isUser ? (
          <SafeMarkdown content={displayContent} />
        ) : (
          <FormattedAgentResponse content={displayContent} agentName={message.agentName ?? undefined} />
        )}
        {message.isStreaming && (
          <span className="ml-0.5 inline-block h-4 w-1 animate-pulse bg-cyan-400" />
        )}
        {message.isStreaming && (
          <span className="ml-0.5 inline-block h-4 w-1 animate-pulse bg-cyan-400" />
        )}
        {isLong && (
          <button
            type="button"
            onClick={() => setExpanded((v) => !v)}
            className="mt-2 flex items-center gap-1 text-xs text-blue-300 hover:text-blue-200 transition-all duration-200"
            data-testid="collapse-toggle"
          >
            {expanded ? (
              <>
                <ChevronUp size={12} /> Show less
              </>
            ) : (
              <>
                <ChevronDown size={12} /> Show more
              </>
            )}
          </button>
        )}
        {message.structuredData && (
          <StructuredDataSummary data={message.structuredData} />
        )}
        {message.expandableReasoning && (
          <ExpandableReasoning text={message.expandableReasoning} />
        )}
        {approvalOrders.length > 0 && (
          <InlineApprovalButtons orders={approvalOrders} />
        )}
      </div>
    </div>
  );
}
