import { SafeMarkdown } from "@/lib/markdown";
import { CheckCircle, XCircle, AlertTriangle, TrendingUp, Package } from "lucide-react";

interface FormattedAgentResponseProps {
  content: string;
  agentName?: string;
}

interface ExtractedData {
  orderIds: string[];
  recommendations: Array<{ orderId: string; recommendation: string; category: string }>;
  capacityMetrics: Array<{ label: string; value: string }>;
  decisions: Array<{ orderId: string; decision: string }>;
}

function extractStructuredData(content: string): ExtractedData {
  const data: ExtractedData = {
    orderIds: [],
    recommendations: [],
    capacityMetrics: [],
    decisions: [],
  };

  // Extract order IDs (PO-YYYY-NNN format)
  const orderIdPattern = /PO-\d{4}-\d{3}/g;
  const matches = content.match(orderIdPattern);
  if (matches) {
    data.orderIds = [...new Set(matches)];
  }

  // Extract recommendations
  const recommendationPattern = /(PO-\d{4}-\d{3}).*?(Transfer|Non-transferable|Transfer on overtime|Transfer on weekend|Transfer with procurement)/gi;
  let match;
  while ((match = recommendationPattern.exec(content)) !== null) {
    data.recommendations.push({
      orderId: match[1] ?? "",
      recommendation: match[2] ?? "",
      category: match[2] ?? "",
    });
  }

  // Extract capacity metrics (hours, tons, operators)
  const capacityPattern = /(\d+\.?\d*)\s*(hrs?|hours?|tons?|operators?)/gi;
  while ((match = capacityPattern.exec(content)) !== null) {
    data.capacityMetrics.push({
      label: match[2] ?? "",
      value: match[1] ?? "",
    });
  }

  // Extract decisions (APPROVED, REJECTED, SKIPPED)
  const decisionPattern = /(PO-\d{4}-\d{3}).*?(APPROVED|REJECTED|SKIPPED|approved|rejected|skipped)/gi;
  while ((match = decisionPattern.exec(content)) !== null) {
    data.decisions.push({
      orderId: match[1] ?? "",
      decision: (match[2] ?? "").toUpperCase(),
    });
  }

  return data;
}

export function FormattedAgentResponse({ content, agentName }: FormattedAgentResponseProps) {
  const extracted = extractStructuredData(content);

  // If no structured data found, just render markdown
  if (
    extracted.orderIds.length === 0 &&
    extracted.recommendations.length === 0 &&
    extracted.decisions.length === 0
  ) {
    return (
      <div className="prose prose-invert prose-sm max-w-none">
        <SafeMarkdown content={content} />
      </div>
    );
  }

  return (
    <div>
      {/* Main content */}
      <div className="space-y-3">
        <SafeMarkdown content={content} />
      </div>

      {/* Extracted structured data */}
      <div className="space-y-2 pt-4 mt-4 border-t border-blue-700/30">
        {/* Decisions */}
        {extracted.decisions.length > 0 && (
          <div className="rounded-lg bg-blue-950/60 p-3 space-y-2 border border-blue-800/30">
            <div className="flex items-center gap-2 mb-2">
              <TrendingUp size={14} className="text-cyan-300" />
              <span className="text-xs font-semibold text-slate-200">Decisions Made</span>
            </div>
            <div className="space-y-1.5">
              {extracted.decisions.map((decision, idx) => (
                <div
                  key={idx}
                  className="flex items-center justify-between rounded-lg bg-blue-900/40 px-3 py-2 border border-blue-800/20"
                >
                  <span className="text-xs font-mono text-slate-300">{decision.orderId}</span>
                  <div className="flex items-center gap-1.5">
                    {decision.decision === "APPROVED" && (
                      <>
                        <CheckCircle size={12} className="text-emerald-400" />
                        <span className="text-xs font-semibold text-emerald-400">Approved</span>
                      </>
                    )}
                    {decision.decision === "REJECTED" && (
                      <>
                        <XCircle size={12} className="text-red-400" />
                        <span className="text-xs font-semibold text-red-400">Rejected</span>
                      </>
                    )}
                    {decision.decision === "SKIPPED" && (
                      <>
                        <AlertTriangle size={12} className="text-yellow-400" />
                        <span className="text-xs font-semibold text-yellow-400">Skipped</span>
                      </>
                    )}
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Recommendations */}
        {extracted.recommendations.length > 0 && (
          <div className="rounded-lg bg-blue-950/60 p-3 space-y-2 border border-blue-800/30">
            <div className="flex items-center gap-2 mb-2">
              <Package size={14} className="text-violet-300" />
              <span className="text-xs font-semibold text-slate-200">Recommendations</span>
            </div>
            <div className="space-y-1.5">
              {extracted.recommendations.map((rec, idx) => (
                <div
                  key={idx}
                  className="flex items-center justify-between rounded-lg bg-blue-900/40 px-3 py-2 border border-blue-800/20"
                >
                  <span className="text-xs font-mono text-slate-300">{rec.orderId}</span>
                  <span
                    className={`text-xs font-medium ${
                      rec.category.toLowerCase().includes("non-transferable")
                        ? "text-red-400"
                        : rec.category.toLowerCase().includes("overtime") ||
                          rec.category.toLowerCase().includes("weekend") ||
                          rec.category.toLowerCase().includes("procurement")
                        ? "text-yellow-400"
                        : "text-emerald-400"
                    }`}
                  >
                    {rec.recommendation}
                  </span>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Capacity Metrics Summary */}
        {extracted.capacityMetrics.length > 0 && agentName === "Capacity Optimization" && (
          <div className="rounded-lg bg-blue-950/60 p-3 border border-blue-800/30">
            <div className="flex items-center gap-2 mb-2">
              <TrendingUp size={14} className="text-blue-300" />
              <span className="text-xs font-semibold text-slate-200">Capacity Metrics</span>
            </div>
            <div className="grid grid-cols-2 gap-2">
              {extracted.capacityMetrics.slice(0, 4).map((metric, idx) => (
                <div key={idx} className="rounded-lg bg-blue-900/40 px-3 py-2 border border-blue-800/20">
                  <span className="text-xs text-slate-400">{metric.label}</span>
                  <p className="text-sm font-semibold text-blue-300">{metric.value}</p>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
