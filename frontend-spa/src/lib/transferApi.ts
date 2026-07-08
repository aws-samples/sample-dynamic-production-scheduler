/**
 * Transfer API — DynamoDB-backed transfer request CRUD via REST proxy.
 */

import { useStore } from "@/store";
import { useAuthStore } from "@/store/auth";
import { signedFetch } from "@/lib/sigv4";
import { logger } from "@/lib/logger";
import type { TransferRequest, PlantId, UiTransferOrder } from "@/types";

let API_URL: string | undefined = import.meta.env.VITE_API_URL as string | undefined;

async function getApiUrl(): Promise<string | undefined> {
  if (API_URL) return API_URL;
  try {
    const resp = await fetch("/config.json");
    if (resp.ok) {
      const config = await resp.json();
      if (config.VITE_API_URL) API_URL = config.VITE_API_URL;
    }
  } catch { /* ignore */ }
  return API_URL;
}

async function apiCall(body: Record<string, unknown>): Promise<Record<string, unknown> | null> {
  const url = await getApiUrl();
  if (!url) return null;
  let credentials = useAuthStore.getState().credentials;
  if (!credentials) credentials = await useAuthStore.getState().refreshCredentials();
  const resp = await signedFetch(url, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  }, credentials);
  if (!resp.ok) {
    logger.info("TransferAPI", `API returned ${resp.status}`);
    return null;
  }
  const raw = await resp.json();
  return raw.body ? (typeof raw.body === "string" ? JSON.parse(raw.body) : raw.body) : raw;
}

/** Track submitted order IDs to prevent duplicate writes */
const _submittedOrders = new Set<string>();

/** Submit transfer orders to DynamoDB (called after constraint funnel completes). */
export async function submitTransfers(
  orders: UiTransferOrder[],
  sourcePlant: PlantId,
  targetPlant: PlantId,
): Promise<string[]> {
  // Deduplicate — skip orders already submitted in this session
  const newOrders = orders.filter((o) => !_submittedOrders.has(o.orderId));
  if (newOrders.length === 0) {
    logger.info("TransferAPI", `All ${orders.length} orders already submitted, skipping`);
    return [];
  }
  newOrders.forEach((o) => _submittedOrders.add(o.orderId));

  const sessionId = useStore.getState().session.sessionId;
  const data = await apiCall({
    action: "transfer_submit",
    source_plant: sourcePlant,
    target_plant: targetPlant,
    transfers: newOrders,
    sessionId: sessionId || "",
  });
  if (!data) return [];
  const ids = (data.transfer_ids as string[]) || [];
  logger.info("TransferAPI", `Submitted ${ids.length} transfers`);
  return ids;
}

/** Fetch transfers for a plant from DynamoDB. Filters to current session. */
export async function fetchTransfers(
  plant: PlantId,
  direction: "incoming" | "outgoing",
): Promise<TransferRequest[]> {
  const data = await apiCall({ action: "transfer_list", plant, direction });
  if (!data) return [];
  const items = (data.transfers as Record<string, unknown>[]) || [];
  // Filter to current session only — if no session yet, return empty
  const sessionId = useStore.getState().session.sessionId;
  if (!sessionId) return [];
  const sessionItems = items.filter((item) => item.session_id === sessionId);
  return sessionItems.map((item) => {
    const od = (item.order_data as Record<string, unknown>) || {};
    return {
      id: item.transfer_id as string,
      orderId: (item.order_id as string) || (od.orderId as string) || "",
      order: {
        orderId: (od.orderId as string) || (item.order_id as string) || "",
        plant: (item.source_plant as PlantId) || "Florida",
        productFamily: (od.product as string) || "",
        quantity: Number(od.quantity || 0),
        dueDate: (od.dueDate as string) || "",
        customerName: (od.customer as string) || "",
        customerTier: ((od.customerTier as string) || "Tier1") as "Tier1" | "Tier2" | "Tier3",
        orderValue: parseFloat(String(od.value || "0").replace(/[^0-9.]/g, "")) || 0,
        priority: (od.priority || null) as "P1" | "P2" | "P3" | null,
        status: "Active",
        transferredFrom: null,
      },
      recommendation: (item.recommendation as string) || "",
      reasoning: (item.reasoning as string) || "",
      funnelResults: ((item.funnel_results as Array<Record<string, unknown>>) || []).map((f) => ({
        layer: f.layer as 1 | 2 | 3 | 4,
        name: f.name as "Equipment" | "Material" | "Utilization" | "Cascade",
        passed: f.passed as boolean,
        detail: (f.detail as string) || "",
      })),
      status: (item.status as TransferRequest["status"]) || "submitted_for_review",
      declineReason: (item.decline_reason as string) || undefined,
      proposedAt: (item.created_at as string) || new Date().toISOString(),
      decidedAt: item.updated_at !== item.created_at ? (item.updated_at as string) : undefined,
    };
  });
}

/** Accept or reject a transfer in DynamoDB. */
export async function decideTransfer(
  transferId: string,
  decision: "approved" | "declined",
  reason?: string,
): Promise<boolean> {
  const data = await apiCall({
    action: "transfer_decide",
    transfer_id: transferId,
    decision,
    reason: reason || "",
  });
  return !!data;
}

let pollInterval: ReturnType<typeof setInterval> | null = null;

/** Start polling for transfer updates. */
export function startTransferPolling(plant: PlantId): void {
  if (pollInterval) return;
  const poll = async () => {
    try {
      const [incoming, outgoing] = await Promise.all([
        fetchTransfers(plant, "incoming"),
        fetchTransfers(plant, "outgoing"),
      ]);
      const all = [...incoming, ...outgoing];
      if (all.length > 0) {
        useStore.getState().setTransferRequests(all);
      }
    } catch (e) {
      logger.info("TransferAPI", `Poll error: ${e}`);
    }
  };
  poll(); // immediate first fetch
  pollInterval = setInterval(poll, 10000); // every 10s
}

/** Stop polling. */
export function stopTransferPolling(): void {
  if (pollInterval) {
    clearInterval(pollInterval);
    pollInterval = null;
  }
}
