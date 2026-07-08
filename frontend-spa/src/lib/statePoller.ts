/**
 * State poller — fetches session state from DynamoDB via the REST proxy's
 * `session_state` action and writes structured data to the Zustand store.
 *
 * This is the DynamoDB-as-source-of-truth path. It runs after each chat
 * response and can also be called on an interval for live updates.
 */

import { useStore } from "@/store";
import { useAuthStore } from "@/store/auth";
import { signedFetch } from "@/lib/sigv4";
import { logger } from "@/lib/logger";
import type { CapacitySnapshot, DisruptionPhase, FunnelOrder, FunnelLayerResult } from "@/types";

let API_URL: string | undefined;

async function getApiUrl(): Promise<string | undefined> {
  if (API_URL) return API_URL;
  API_URL = import.meta.env.VITE_API_URL as string | undefined;
  if (API_URL) return API_URL;
  try {
    const resp = await fetch("/config.json");
    if (resp.ok) {
      const config = await resp.json();
      if (config.VITE_API_URL) API_URL = config.VITE_API_URL;
    }
  } catch { /* config.json not found */ }
  return API_URL;
}

/** Phase mapping from DynamoDB state_key values to frontend DisruptionPhase */
const PHASE_MAP: Record<string, DisruptionPhase> = {
  round1_complete: "round1",
  delay_optimization: "delay_optimization",
  round2_delays: "delay_optimization",
  constraint_funnel: "constraint_funnel",
  round2_funnel: "constraint_funnel",
  capacity_summary: "capacity_summary",
  summary: "complete",
  complete: "complete",
};

/**
 * Poll the session_state endpoint and update the Zustand store.
 * Returns true if data was found, false otherwise.
 */
export async function pollSessionState(): Promise<boolean> {
  const store = useStore.getState();
  const sessionId = store.session.sessionId;
  if (!sessionId || sessionId.length < 10) return false;

  const url = await getApiUrl();
  if (!url) return false;

  try {
    let credentials = useAuthStore.getState().credentials;
    if (!credentials) {
      credentials = await useAuthStore.getState().refreshCredentials();
    }

    let resp = await signedFetch(
      url,
      {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ action: "session_state", sessionId }),
      },
      credentials,
    );

    // Retry once with fresh credentials on 403 (expired token)
    if (resp.status === 403) {
      credentials = await useAuthStore.getState().refreshCredentials();
      resp = await signedFetch(
        url,
        {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ action: "session_state", sessionId }),
        },
        credentials,
      );
    }

    if (!resp.ok) {
      logger.info("StatePoller", `session_state returned ${resp.status}`);
      return false;
    }

    const raw = await resp.json();
    const data = raw.body ? (typeof raw.body === "string" ? JSON.parse(raw.body) : raw.body) : raw;

    const ws = data.workflowState || {};
    const tracker = data.tracker || null;

    // --- Phase ---
    // Only allow forward transitions — never regress to an earlier phase
    const PHASE_ORDER: DisruptionPhase[] = ["landing", "round1", "delay_optimization", "constraint_funnel", "capacity_summary", "complete"];
    const phaseData = ws.current_phase;
    if (phaseData && typeof phaseData === "object" && phaseData.phase) {
      const mapped = PHASE_MAP[phaseData.phase];
      if (mapped && store.disruption && store.disruption.phase !== mapped) {
        const currentIdx = PHASE_ORDER.indexOf(store.disruption.phase);
        const newIdx = PHASE_ORDER.indexOf(mapped);
        if (newIdx > currentIdx) {
          store.setDisruptionPhase(mapped);
          logger.info("StatePoller", `Phase updated: ${mapped}`);
        } else {
          logger.info("StatePoller", `Blocked backward phase: ${store.disruption.phase} → ${mapped}`);
        }
      }
    }

    // --- Capacity from CO output ---
    const co = ws.round1_co;
    if (co && typeof co === "object" && store.disruption) {
      if (!store.disruption.capacityResults) {
        const util = co.utilization || [];
        const rmUtil = util.find((u: Record<string, unknown>) => u.machine_type === "Rolling Mill");
        const flUtil = util.find((u: Record<string, unknown>) => u.machine_type === "Finishing Line");
        const rmPct = rmUtil?.normal_utilization_pct ?? 0;
        const flPct = flUtil?.normal_utilization_pct ?? 0;
        const snapshot: CapacitySnapshot = {
          rollingMill: { label: "Rolling Mill", used: rmPct, available: 100 - rmPct, unit: "%", thresholdPct: 85 },
          finishingLine: { label: "Finishing Line", used: flPct, available: 100 - flPct, unit: "%", thresholdPct: 85 },
          materialTons: { label: "Raw Material", used: co.material_utilization_pct ?? 0, available: 100 - (co.material_utilization_pct ?? 0), unit: "%", thresholdPct: 85 },
          operatorHours: { label: "Workforce", used: co.workforce_utilization_pct ?? 0, available: 100 - (co.workforce_utilization_pct ?? 0), unit: "%", thresholdPct: 85 },
          bottleneck: co.bottleneck || "Unknown",
          lastUpdated: new Date().toISOString(),
        };
        store.setDisruptionCapacityResults(snapshot);
      }
    }

    // --- Impact Assessment (IA) output — scored orders ---
    const ia = ws.round1_ia;
    if (ia && typeof ia === "object" && store.disruption) {
      const scoredOrders = (ia as Record<string, unknown>).scored_orders;
      if (Array.isArray(scoredOrders) && scoredOrders.length > 0) {
        const mapped = scoredOrders.map((o: Record<string, unknown>) => ({
          orderId: (o.order_id || "") as string,
          plant: (store.disruption?.plant || "Florida") as "Florida" | "Ohio",
          productFamily: (o.product_family || "") as string,
          quantity: Number(o.quantity || 0),
          dueDate: (o.due_date || "") as string,
          customerName: (o.customer_name || o.customer_id || "") as string,
          customerTier: (o.customer_tier || "Tier3") as "Tier1" | "Tier2" | "Tier3",
          orderValue: Number(o.order_value || 0),
          priority: (o.priority || null) as "P1" | "P2" | "P3" | null,
          status: "Active",
        }));
        // Only load once — DynamoDB data doesn't change for IA results
        if (store.disruption.impactResults.length === 0) {
          store.setDisruptionImpactResults(mapped);
          logger.info("StatePoller", `Impact results loaded: ${mapped.length} orders`);
        }
      }
    }

    // --- Delay candidates ---
    const candidates = ws.delay_candidates;
    if (Array.isArray(candidates) && candidates.length > 0 && store.disruption) {
      const receivingPlant = store.disruption.plant === "Florida" ? "Ohio" : "Florida";
      const mapped = candidates.map((c: Record<string, unknown>) => ({
        orderId: (c.order_id || "") as string,
        order: {
          orderId: (c.order_id || "") as string,
          plant: receivingPlant as "Florida" | "Ohio",
          productFamily: (c.product_family || "") as string,
          quantity: 0,
          dueDate: (c.due_date || "") as string,
          customerName: (c.customer_id || "") as string,
          customerTier: (c.customer_tier || "Tier3") as "Tier1" | "Tier2" | "Tier3",
          orderValue: Number(c.order_value || 0),
          priority: "P3" as "P1" | "P2" | "P3" | null,
          status: "Active",
        },
        freedCapacity: `RM +${c.freed_rolling_mill_hours || 0}h, FL +${c.freed_finishing_line_hours || 0}h`,
        impactSummary: (c.trade_off_explanation || "") as string,
      }));
      // Always update from DynamoDB — but only if the user hasn't started deciding yet
      if (store.disruption.delayCandidates.length === 0) {
        store.setDisruptionDelayCandidates(mapped);
        logger.info("StatePoller", `Delay candidates loaded: ${mapped.length}`);
      } else {
        logger.info("StatePoller", `Delay candidates already in store: ${store.disruption.delayCandidates.length}, skipping update`);
      }
      // NOTE: delay_index is NOT synced from DynamoDB — the frontend owns it
    }

    // --- Funnel results from Constraint Matching ---
    const funnelResults = ws.funnel_results;
    if (funnelResults && typeof funnelResults === "object" && store.disruption) {
      const funnelItems = (funnelResults as Record<string, unknown>).funnel_results;
      if (Array.isArray(funnelItems) && funnelItems.length > 0) {
        const receivingPlant = store.disruption.plant === "Florida" ? "Ohio" : "Florida";
        const mapped: FunnelOrder[] = funnelItems.map((fr: Record<string, unknown>) => ({
          orderId: (fr.order_id || "") as string,
          order: {
            orderId: (fr.order_id || "") as string,
            plant: receivingPlant as "Florida" | "Ohio",
            productFamily: (fr.product_family || "") as string,
            quantity: 0,
            dueDate: (fr.due_date || "") as string,
            customerName: (fr.customer_id || "") as string,
            customerTier: (fr.customer_tier || "Tier3") as "Tier1" | "Tier2" | "Tier3",
            orderValue: Number(fr.order_value || 0),
            priority: (fr.priority || "P3") as "P1" | "P2" | "P3" | null,
            status: "Active",
          },
          funnelResults: Array.isArray(fr.layers)
            ? (fr.layers as Record<string, unknown>[]).map((l) => ({
                layer: (l.layer || 0) as FunnelLayerResult["layer"],
                name: (l.name || "") as FunnelLayerResult["name"],
                passed: !!l.passed,
                detail: (l.detail || "") as string,
              }))
            : [],
          recommendation: (fr.recommendation || "") as string,
          reasoning: (fr.reasoning || "") as string,
        }));
        // Load funnel orders if store is empty OR if the count changed (new results arrived)
        const currentCount = store.disruption.funnelOrders.length;
        if (currentCount === 0 || (currentCount !== mapped.length && store.disruption.currentFunnelIndex === 0)) {
          store.setDisruptionFunnelOrders(mapped);
          logger.info("StatePoller", `Funnel orders loaded: ${mapped.length}`);
        }
      }
    }

    // --- Capacity impact (from tracker or CO output) ---
    if (store.disruption && !store.disruption.capacityImpact) {
      const receivingPlant = store.disruption.plant === "Florida" ? "Ohio" : "Florida";
      const rmPct = Number(co?.utilization?.find((u: Record<string, unknown>) => u.machine_type === "Rolling Mill")?.normal_utilization_pct ?? 0);
      const flPct = Number(co?.utilization?.find((u: Record<string, unknown>) => u.machine_type === "Finishing Line")?.normal_utilization_pct ?? 0);
      const overallPct = (rmPct + flPct) / 2;

      if (co) {
        // Initialize with current = projected (no decisions made yet).
        // Decisions in DelayCardQueue/ConstraintFunnelView adjust projected locally.
        store.setDisruptionCapacityImpact({
          senderPlant: {
            name: store.disruption.plant,
            rollingMill: { current: 100, projected: 100 },
            finishingLine: { current: 100, projected: 100 },
            overall: { current: 100, projected: 100 },
          },
          receiverPlant: {
            name: receivingPlant,
            rollingMill: { current: rmPct, projected: rmPct },
            finishingLine: { current: flPct, projected: flPct },
            overall: { current: overallPct, projected: overallPct },
          },
        });
        logger.info("StatePoller", `Capacity impact initialized: RM=${rmPct}%, FL=${flPct}%`);
      }
    }

    logger.info("StatePoller", `Polled session state: ws_keys=${Object.keys(ws).join(",")}, tracker=${!!tracker}`);
    return true;
  } catch (err) {
    logger.info("StatePoller", `Poll failed: ${err}`);
    return false;
  }
}

/** Interval handle for auto-polling */
let pollInterval: ReturnType<typeof setInterval> | null = null;

/** Start polling every N ms. Stops any existing interval first. */
export function startPolling(intervalMs = 2000): void {
  stopPolling();
  pollInterval = setInterval(() => { pollSessionState(); }, intervalMs);
  logger.info("StatePoller", `Started polling every ${intervalMs}ms`);
}

/** Stop auto-polling. */
export function stopPolling(): void {
  if (pollInterval) {
    clearInterval(pollInterval);
    pollInterval = null;
    logger.info("StatePoller", "Stopped polling");
  }
}
