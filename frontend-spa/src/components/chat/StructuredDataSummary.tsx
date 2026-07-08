import type { StructuredPayload } from "@/types";
import { useStore } from "@/store";

interface StructuredDataSummaryProps {
  data: StructuredPayload;
}

export function StructuredDataSummary({ data }: StructuredDataSummaryProps) {
  const showDetail = useStore((s) => s.showDetail);

  return (
    <div className="mt-2 rounded-lg border border-white/[0.06] bg-slate-800/80 p-2">
      <p className="text-xs font-medium text-slate-300">{data.title}</p>
      <button
        data-testid="view-details-btn"
        className="mt-1 min-h-11 min-w-11 text-xs text-cyan-400 underline hover:text-cyan-300 transition-all duration-200"
        onClick={() => showDetail(data)}
      >
        View details
      </button>
    </div>
  );
}
