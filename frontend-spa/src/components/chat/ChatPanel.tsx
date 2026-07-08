import { ChatPanelBoundary } from "@/components/errors/ChatPanelBoundary";
import { MessageList } from "./MessageList";
import { MessageInput } from "./MessageInput";
import { CapacityTrackerPanel } from "./CapacityTrackerPanel";

export function ChatPanel() {
  return (
    <ChatPanelBoundary>
      <div className="flex flex-1 flex-col overflow-hidden bg-slate-950">
        <div className="flex-1 overflow-hidden flex flex-col">
          <MessageList />
        </div>
        <div className="border-t border-white/[0.06] p-3">
          <CapacityTrackerPanel />
        </div>
        <MessageInput />
      </div>
    </ChatPanelBoundary>
  );
}
