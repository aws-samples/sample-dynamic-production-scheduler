import { useState, useCallback, type KeyboardEvent } from "react";
import { useStore } from "@/store";
import { send } from "@/lib/streaming";

const MAX_LENGTH = 2000;

export function MessageInput() {
  const [text, setText] = useState("");
  const status = useStore((s) => s.connection.status);
  const isTyping = useStore((s) => s.chat.isAgentTyping);
  const sessionId = useStore((s) => s.session.sessionId);

  const disabled = status !== "connected" || isTyping;

  const handleSend = useCallback(() => {
    const trimmed = text.trim();
    if (!trimmed || disabled) return;

    const id = crypto.randomUUID();
    useStore.getState().addUserMessage(id, trimmed);
    send({ action: "sendMessage", data: trimmed });
    setText("");
  }, [text, disabled, sessionId]);

  const handleKey = (e: KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  return (
    <div className="flex items-end gap-2 border-t border-white/[0.06] bg-slate-900 p-3">
      <textarea
        data-testid="chat-input-field"
        className="flex-1 resize-none rounded-lg border border-white/[0.08] bg-slate-800/80 px-3 py-2 text-sm text-slate-100 placeholder-slate-500 focus:border-cyan-500/40 focus:outline-none disabled:opacity-50 transition-all duration-200"
        rows={1}
        maxLength={MAX_LENGTH}
        placeholder={disabled ? "Waiting..." : "Type a message..."}
        value={text}
        disabled={disabled}
        onChange={(e) => setText(e.target.value)}
        onKeyDown={handleKey}
      />
      <button
        data-testid="chat-send-btn"
        className="min-h-11 min-w-11 rounded-lg bg-gradient-to-r from-cyan-500 to-teal-500 px-4 py-2 text-sm font-medium text-white hover:from-cyan-400 hover:to-teal-400 disabled:opacity-40 transition-all duration-200"
        disabled={disabled || !text.trim()}
        onClick={handleSend}
        aria-label="Send message"
      >
        Send
      </button>
    </div>
  );
}
