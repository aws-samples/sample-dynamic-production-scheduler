import { useState, useCallback, useRef, useEffect, type KeyboardEvent } from "react";
import { useStore } from "@/store";
import { sendMessage } from "@/lib/streaming";
import { MessageSquare, X, Send } from "lucide-react";

interface WhatIfMessage {
  id: string;
  role: "user" | "assistant";
  content: string;
  timestamp: string;
}

export function WhatIfChat() {
  const [open, setOpen] = useState(false);
  const [text, setText] = useState("");
  const [messages, setMessages] = useState<WhatIfMessage[]>([]);
  const [waiting, setWaiting] = useState(false);
  const listRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (listRef.current) {
      listRef.current.scrollTop = listRef.current.scrollHeight;
    }
  }, [messages]);

  // Watch for new assistant messages that look like what-if responses
  const chatMessages = useStore((s) => s.chat.messages);
  const lastMsg = chatMessages[chatMessages.length - 1];
  useEffect(() => {
    if (waiting && lastMsg?.role === "assistant" && !lastMsg.isStreaming) {
      setMessages((prev) => [
        ...prev,
        { id: lastMsg.id, role: "assistant", content: lastMsg.content, timestamp: lastMsg.timestamp },
      ]);
      setWaiting(false);
      // Tag the assistant response as WhatIf so phase views filter it out
      const store = useStore.getState();
      const msgs = store.chat.messages.map((m) =>
        m.id === lastMsg.id ? { ...m, agentName: "WhatIf" } : m,
      );
      useStore.setState({ chat: { ...store.chat, messages: msgs } });
    }
  }, [lastMsg?.id, lastMsg?.isStreaming, waiting]);

  const handleSend = useCallback(async () => {
    const trimmed = text.trim();
    if (!trimmed || waiting) return;

    setMessages((prev) => [
      ...prev,
      { id: crypto.randomUUID(), role: "user", content: trimmed, timestamp: new Date().toISOString() },
    ]);
    setText("");
    setWaiting(true);
    // Tag the user message with "WhatIf" agent so phase views can filter it out
    const msgId = crypto.randomUUID();
    const store = useStore.getState();
    store.addUserMessage(msgId, `What-if question: ${trimmed}`);
    // Mark the user message as what-if by setting agentName
    const msgs = store.chat.messages.map((m) =>
      m.id === msgId ? { ...m, agentName: "WhatIf" } : m,
    );
    useStore.setState({ chat: { ...store.chat, messages: msgs } });
    await sendMessage(`What-if question: ${trimmed}`);
  }, [text, waiting]);

  const handleKey = (e: KeyboardEvent<HTMLInputElement>) => {
    if (e.key === "Enter") {
      e.preventDefault();
      handleSend();
    }
  };

  if (!open) {
    return (
      <button
        onClick={() => setOpen(true)}
        className="fixed bottom-6 right-6 z-40 flex items-center gap-2 rounded-full bg-blue-600 px-4 py-3 text-sm font-medium text-white shadow-lg transition-colors hover:bg-blue-500"
        data-testid="whatif-toggle-btn"
        aria-label="Open what-if chat"
      >
        <MessageSquare size={16} /> Ask What-If
      </button>
    );
  }

  return (
    <div
      className="fixed bottom-6 right-6 z-40 flex h-96 w-80 flex-col rounded-xl border border-gray-200 bg-white shadow-2xl"
      data-testid="whatif-chat-panel"
    >
      {/* Header */}
      <div className="flex items-center justify-between border-b border-gray-200 px-4 py-3">
        <span className="text-sm font-semibold text-gray-700">What-If Analysis</span>
        <button
          onClick={() => setOpen(false)}
          className="rounded p-1 text-gray-400 hover:bg-gray-100 hover:text-gray-600"
          aria-label="Close what-if chat"
          data-testid="whatif-close-btn"
        >
          <X size={16} />
        </button>
      </div>

      {/* Messages */}
      <div ref={listRef} className="flex-1 overflow-y-auto p-3 space-y-2">
        {messages.length === 0 && (
          <p className="py-8 text-center text-xs text-gray-400">
            Ask what-if questions about the disruption scenario
          </p>
        )}
        {messages.map((m) => (
          <div
            key={m.id}
            className={`rounded-lg px-3 py-2 text-xs ${
              m.role === "user"
                ? "ml-8 bg-blue-50 text-blue-900"
                : "mr-8 bg-gray-100 text-gray-700"
            }`}
          >
            {m.content}
          </div>
        ))}
        {waiting && (
          <div className="mr-8 rounded-lg bg-gray-100 px-3 py-2 text-xs text-gray-400">
            Thinking...
          </div>
        )}
      </div>

      {/* Input */}
      <div className="flex items-center gap-2 border-t border-gray-200 p-3">
        <input
          type="text"
          value={text}
          onChange={(e) => setText(e.target.value)}
          onKeyDown={handleKey}
          placeholder="e.g. What if I add weekend shifts?"
          className="flex-1 rounded-lg border border-gray-300 px-3 py-2 text-xs text-gray-900 placeholder-gray-400 focus:border-blue-500 focus:outline-none"
          disabled={waiting}
          data-testid="whatif-input"
        />
        <button
          onClick={handleSend}
          disabled={waiting || !text.trim()}
          className="rounded-lg bg-blue-600 p-2 text-white hover:bg-blue-500 disabled:opacity-40"
          aria-label="Send what-if question"
          data-testid="whatif-send-btn"
        >
          <Send size={14} />
        </button>
      </div>
    </div>
  );
}
