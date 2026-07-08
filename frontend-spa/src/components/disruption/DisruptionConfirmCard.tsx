import { useState } from "react";
import { useStore } from "@/store";
import { sendMessage } from "@/lib/streaming";
import {
  AlertTriangle,
  Factory,
  Clock,
  Zap,
  BarChart3,
  ArrowRightLeft,
  FileText,
  Play,
} from "lucide-react";

interface ConfirmCardProps {
  content: string;
  plant: string;
}

/** Parse key details from the orchestrator's confirmation response */
function parseConfirmation(text: string) {
  const eventType =
    text.match(/event\s*type[:\s]*([^\n|]+)/i)?.[1]?.trim() ??
    text.match(/hurricane|tornado|earthquake|flood|fire|shutdown|equipment failure/i)?.[0] ??
    "Disruption";
  const scope =
    text.match(/scope[:\s]*([^\n|]+)/i)?.[1]?.trim() ??
    (text.match(/complete shutdown/i) ? "Complete shutdown" : "Production affected");
  const systems =
    text.match(/systems?\s*status[:\s]*([^\n|]+)/i)?.[1]?.trim() ??
    (text.match(/offline/i) ? "Equipment and systems offline" : "");
  const duration =
    text.match(/(?:expected\s*)?duration[:\s]*([^\n|]+)/i)?.[1]?.trim() ??
    text.match(/\d+\+?\s*weeks?/i)?.[0] ??
    "";

  return { eventType, scope, systems, duration };
}

export function DisruptionConfirmCard({ content, plant }: ConfirmCardProps) {
  const [starting, setStarting] = useState(false);
  const { eventType, scope, systems, duration } = parseConfirmation(content);

  async function handleBegin() {
    setStarting(true);
    const msg =
      "Yes, confirmed. Proceed with the disruption response workflow immediately. Begin Round 1 intelligence gathering now.";
    useStore.getState().addUserMessage(crypto.randomUUID(), msg);
    await sendMessage(msg);
    setStarting(false);
  }

  const details = [
    { icon: AlertTriangle, label: "Event", value: eventType, color: "text-red-600" },
    { icon: Factory, label: "Plant", value: `${plant} Plant`, color: "text-blue-600" },
    { icon: Zap, label: "Scope", value: scope, color: "text-amber-600" },
    ...(systems ? [{ icon: Factory, label: "Systems", value: systems, color: "text-gray-600" }] : []),
    ...(duration ? [{ icon: Clock, label: "Duration", value: duration, color: "text-purple-600" }] : []),
  ];

  const steps = [
    { icon: BarChart3, label: "Round 1", desc: "Analyze & prioritize affected orders, assess receiving plant capacity" },
    { icon: ArrowRightLeft, label: "Round 2", desc: "Optimize delays and run constraint funnel for rerouting" },
    { icon: FileText, label: "Summary", desc: "Generate recommendations and capacity impact report" },
  ];

  return (
    <div
      className="rounded-xl border border-red-200 bg-white shadow-sm overflow-hidden"
      data-testid="disruption-confirm-card"
    >
      {/* Header */}
      <div className="bg-red-50 px-6 py-4 border-b border-red-100">
        <div className="flex items-center gap-3">
          <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-red-100">
            <AlertTriangle size={20} className="text-red-600" />
          </div>
          <div>
            <h3 className="text-base font-semibold text-gray-900">Disruption Confirmed</h3>
            <p className="text-xs text-gray-500">Review details and begin the response workflow</p>
          </div>
        </div>
      </div>

      {/* Details grid */}
      <div className="px-6 py-4">
        <div className="grid grid-cols-2 gap-3 sm:grid-cols-3">
          {details.map((d, i) => (
            <div key={i} className="rounded-lg bg-gray-50 p-3">
              <div className="flex items-center gap-2 mb-1">
                <d.icon size={14} className={d.color} />
                <span className="text-[10px] font-medium uppercase tracking-wide text-gray-400">
                  {d.label}
                </span>
              </div>
              <p className="text-sm font-medium text-gray-800">{d.value}</p>
            </div>
          ))}
        </div>
      </div>

      {/* Workflow steps */}
      <div className="px-6 pb-4">
        <p className="text-xs font-medium text-gray-500 mb-3">Workflow Steps</p>
        <div className="space-y-2">
          {steps.map((s, i) => (
            <div key={i} className="flex items-start gap-3">
              <div className="flex h-7 w-7 shrink-0 items-center justify-center rounded-full bg-blue-50">
                <s.icon size={14} className="text-blue-600" />
              </div>
              <div>
                <p className="text-sm font-medium text-gray-800">{s.label}</p>
                <p className="text-xs text-gray-500">{s.desc}</p>
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Action */}
      <div className="border-t border-gray-100 px-6 py-4 bg-gray-50">
        <button
          onClick={handleBegin}
          disabled={starting}
          className="flex w-full items-center justify-center gap-2 rounded-lg bg-red-600 py-3 text-sm font-semibold text-white shadow-sm transition-colors hover:bg-red-500 disabled:opacity-40"
          data-testid="begin-workflow-btn"
        >
          {starting ? (
            "Starting Workflow..."
          ) : (
            <>
              <Play size={16} /> Begin Disruption Response
            </>
          )}
        </button>
      </div>
    </div>
  );
}
