import { useEffect, useRef } from "react";
import { useStore } from "@/store";
import { ChatMessage } from "./ChatMessage";

export function MessageList() {
  const messages = useStore((s) => s.chat.messages);
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages.length, messages[messages.length - 1]?.content]);

  return (
    <div
      className="flex-1 overflow-y-auto px-4 py-3 space-y-3 bg-slate-950"
      role="log"
      aria-live="polite"
    >
      {messages.map((msg, i) => {
        const prev = messages[i - 1];
        const showBadge =
          msg.role === "assistant" &&
          !!msg.agentName &&
          (i === 0 || prev?.agentName !== msg.agentName || prev?.role !== "assistant");

        return <ChatMessage key={msg.id} message={msg} showBadge={showBadge} />;
      })}
      <div ref={bottomRef} />
    </div>
  );
}
