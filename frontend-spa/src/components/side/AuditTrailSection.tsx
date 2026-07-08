import { useState, useEffect, useRef } from "react";
import { useStore } from "@/store";
import { AuditEntryRow } from "./AuditEntryRow";

export function AuditTrailSection() {
  const entries = useStore((s) => s.audit.entries);
  const [open, setOpen] = useState(false);
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (open) bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [entries.length, open]);

  return (
    <div className="border-t border-slate-700">
      <button
        data-testid="audit-trail-toggle"
        className="flex w-full items-center justify-between px-4 py-2 text-xs text-slate-400 hover:bg-slate-750 transition-colors"
        onClick={() => setOpen(!open)}
        aria-expanded={open}
      >
        <span>Audit Trail ({entries.length} entries)</span>
        <span>{open ? "▲" : "▼"}</span>
      </button>
      {open && (
        <div className="max-h-48 overflow-y-auto px-4 pb-2 space-y-1 bg-slate-750">
          {entries.length === 0 && (
            <p className="text-xs text-slate-500">No audit entries yet.</p>
          )}
          {entries.map((entry) => (
            <AuditEntryRow key={entry.id} entry={entry} />
          ))}
          <div ref={bottomRef} />
        </div>
      )}
    </div>
  );
}
