import { useStore } from "@/store";

export function ConnectionIndicator() {
  const status = useStore((s) => s.connection.status);

  if (status === "connected") return null;

  const label =
    status === "reconnecting"
      ? "Reconnecting..."
      : status === "connecting"
        ? "Connecting..."
        : "Disconnected";

  return (
    <span
      className="inline-flex items-center gap-1.5 rounded-full bg-yellow-900/60 px-3 py-1 text-xs text-yellow-200"
      role="status"
      aria-live="polite"
    >
      <span className="h-2 w-2 animate-pulse rounded-full bg-yellow-400" />
      {label}
    </span>
  );
}
