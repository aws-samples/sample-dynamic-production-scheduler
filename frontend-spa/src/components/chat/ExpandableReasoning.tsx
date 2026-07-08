import { useState } from "react";

interface ExpandableReasoningProps {
  text: string;
}

export function ExpandableReasoning({ text }: ExpandableReasoningProps) {
  const [open, setOpen] = useState(false);

  return (
    <div className="mt-2 border-t border-white/[0.06] pt-1">
      <button
        className="min-h-11 min-w-11 text-xs text-slate-400 hover:text-cyan-400 transition-all duration-200"
        onClick={() => setOpen(!open)}
        aria-expanded={open}
      >
        {open ? "Hide reasoning" : "Show reasoning"}
      </button>
      {open && (
        <p className="mt-1 text-xs text-slate-500 whitespace-pre-wrap">{text}</p>
      )}
    </div>
  );
}
