import { useState } from "react";
import { useStore } from "@/store";
import { sendMessage } from "@/lib/streaming";
import { startPolling } from "@/lib/statePoller";
import { AlertTriangle } from "lucide-react";
import type { PlantId } from "@/types";

export function DisruptionLanding() {
  const [plant, setPlant] = useState<PlantId>("Florida");
  const [loading, setLoading] = useState(false);
  const startDisruption = useStore((s) => s.startDisruption);
  const connectionStatus = useStore((s) => s.connection.status);

  async function handleStart() {
    setLoading(true);
    // Clear old chat messages so disruption view starts fresh
    useStore.getState().clearChat();
    startDisruption(plant);
    // Start 2s DynamoDB polling so store data arrives before orchestrator response
    startPolling();
    const msg = `A major disruption has hit the ${plant} plant — a severe weather event (hurricane) has forced a complete shutdown. All active production orders at ${plant} are affected. Equipment and systems are offline. Expected duration: 2+ weeks. Please confirm and begin the disruption response workflow immediately.`;
    useStore.getState().addUserMessage(crypto.randomUUID(), msg);
    await sendMessage(msg);
    setLoading(false);
  }

  return (
    <div className="flex flex-1 flex-col items-center justify-center gap-8 p-8" data-testid="disruption-landing">
      <div className="text-center">
        <div className="mx-auto mb-4 flex h-16 w-16 items-center justify-center rounded-2xl bg-red-100">
          <AlertTriangle size={32} className="text-red-600" />
        </div>
        <h2 className="text-2xl font-semibold text-gray-900">Start Disruption Response</h2>
        <p className="mt-2 max-w-md text-sm text-gray-500">
          Select the affected plant to begin the multi-agent disruption response workflow.
          The system will assess impact, analyze capacity, and guide you through order rerouting.
        </p>
      </div>

      <div className="flex flex-col items-center gap-4">
        <label className="text-sm font-medium text-gray-700" htmlFor="plant-select">
          Affected Plant
        </label>
        <select
          id="plant-select"
          value={plant}
          onChange={(e) => setPlant(e.target.value as PlantId)}
          className="w-56 rounded-lg border border-gray-300 bg-white px-4 py-2.5 text-sm text-gray-700 focus:border-blue-500 focus:ring-2 focus:ring-blue-500/20"
          data-testid="disruption-plant-select"
        >
          <option value="Florida">Miami (Florida)</option>
          <option value="Ohio">Ohio</option>
        </select>

        <button
          onClick={handleStart}
          disabled={loading || connectionStatus !== "connected"}
          className="mt-2 rounded-lg bg-red-600 px-8 py-3 text-sm font-semibold text-white shadow-sm transition-colors hover:bg-red-500 disabled:opacity-40"
          data-testid="disruption-start-btn"
        >
          {loading ? "Starting..." : "Start Disruption Response"}
        </button>
      </div>
    </div>
  );
}
