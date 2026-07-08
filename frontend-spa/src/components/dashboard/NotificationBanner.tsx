import { useStore } from "@/store";
import { AlertTriangle, X } from "lucide-react";

export function NotificationBanner() {
  const planner = useStore((s) => s.planner);
  const notifications = useStore((s) => s.notifications);
  const acknowledge = useStore((s) => s.acknowledgeNotification);

  const unacked = notifications.filter(
    (n) => !n.acknowledged && n.plant === planner?.plant,
  );

  if (unacked.length === 0) return null;

  const latest = unacked[unacked.length - 1]!;

  return (
    <div
      className="mb-6 flex items-center gap-4 rounded-2xl border border-amber-500/20 bg-amber-500/[0.08] px-5 py-4 shadow-lg shadow-amber-500/5"
      role="alert"
      data-testid="notification-banner"
    >
      <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl bg-amber-500/15">
        <AlertTriangle size={20} className="text-amber-400" />
      </div>
      <div className="flex-1">
        <p className="text-sm font-semibold text-amber-300">{latest.title}</p>
        <p className="text-sm text-amber-400/80">{latest.message}</p>
      </div>
      <span className="shrink-0 text-xs text-amber-500/60">
        {new Date(latest.timestamp).toLocaleTimeString()}
      </span>
      <button
        onClick={() => acknowledge(latest.id)}
        className="shrink-0 rounded-lg p-1.5 text-amber-500/50 hover:bg-amber-500/10 hover:text-amber-400 transition-all duration-200"
        data-testid="notification-acknowledge-btn"
        aria-label="Acknowledge notification"
      >
        <X size={16} />
      </button>
    </div>
  );
}
