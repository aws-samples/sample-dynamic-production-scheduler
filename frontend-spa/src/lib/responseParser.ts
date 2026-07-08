/**
 * Response parser — maps structured uiData from the orchestrator's
 * update_ui tool to Zustand store actions. No regex parsing.
 *
 * Rework 6: All structured data comes from msg.uiData (the ui field
 * in the JSON envelope). If uiData is null, we do nothing — the raw
 * text is displayed as markdown in the chat.
 */

import { useStore } from "@/store";
import type { UiPayload } from "@/types";
import { logger } from "@/lib/logger";

/**
 * Process a response and update the store with structured data.
 * Called by streaming.ts after receiving a complete response.
 *
 * @param content - The display text (for chat rendering)
 * @param uiData - Structured UI data from the orchestrator's update_ui tool
 */
export function parseResponse(
  content: string,
  uiData: Record<string, unknown> | null,
): void {
  if (!uiData || Object.keys(uiData).length === 0) {
    return; // No structured data — raw text displayed as markdown
  }

  const store = useStore.getState();
  const ui = uiData as UiPayload;

  // Phase transition — only update if the phase actually changed and the
  // transition is valid. Re-setting the same phase would reset
  // phaseStartMsgCount and hide the message that triggered the transition.
  if (ui.phase) {
    const phaseMap: Record<string, string> = {
      confirmation: "round1",
      round1_analysis: "round1",
      round1_complete: "round1",
      delay_optimization: "delay_optimization",
      constraint_funnel: "constraint_funnel",
      capacity_summary: "capacity_summary",
      summary: "complete",
    };
    const mapped = phaseMap[ui.phase];
    if (mapped && store.disruption && store.disruption.phase !== mapped) {
      // Validate the transition is legal
      const validTransitions: Record<string, string[]> = {
        landing: ["round1"],
        round1: ["delay_optimization", "constraint_funnel", "complete"],
        delay_optimization: ["constraint_funnel", "complete"],
        constraint_funnel: ["capacity_summary", "complete"],
        capacity_summary: ["complete"],
        complete: [],
      };
      const allowed = validTransitions[store.disruption.phase];
      if (!allowed || allowed.includes(mapped)) {
        store.setDisruptionPhase(mapped as import("@/types").DisruptionPhase);
      } else {
        logger.info("ResponseParser", `Blocked invalid phase transition: ${store.disruption.phase} → ${mapped}`);
      }
    }
  }

  // Agent status updates
  if (ui.agents && Array.isArray(ui.agents)) {
    for (const agent of ui.agents) {
      store.setDisruptionAgentStatus(
        agent.name,
        agent.status as "idle" | "running" | "complete" | "error",
        agent.summary ?? null,
      );
    }
  }

  // Capacity snapshot
  if (ui.capacity) {
    // Map UiCapacity percentages to the store's CapacitySnapshot format
    const cap = ui.capacity;
    store.setDisruptionCapacityResults({
      rollingMill: { label: "Rolling Mill", used: cap.rollingMill ?? 0, available: 100 - (cap.rollingMill ?? 0), unit: "%", thresholdPct: 85 },
      finishingLine: { label: "Finishing Line", used: cap.finishingLine ?? 0, available: 100 - (cap.finishingLine ?? 0), unit: "%", thresholdPct: 85 },
      materialTons: { label: "Raw Material", used: cap.rawMaterial ?? 0, available: 100 - (cap.rawMaterial ?? 0), unit: "%", thresholdPct: 85 },
      operatorHours: { label: "Workforce", used: cap.workforce ?? 0, available: 100 - (cap.workforce ?? 0), unit: "%", thresholdPct: 85 },
      bottleneck: (uiData.bottleneck as string) || "Unknown",
      lastUpdated: new Date().toISOString(),
    });
  }

  // Workflow complete
  if (ui.complete) {
    if (store.disruption) {
      store.setDisruptionSummary(content);
      store.setDisruptionPhase("complete");
    }
  }

  // Capacity impact (Rework 7 — live panel data)
  if (ui.capacityImpact) {
    store.setDisruptionCapacityImpact(ui.capacityImpact as unknown as import("@/types").UiCapacityImpact);
  }

  // Transfer orders auto-flow (Rework 7)
  if (ui.transferOrders && Array.isArray(ui.transferOrders)) {
    store.autoFlowTransferOrders(ui.transferOrders as unknown as import("@/types").UiTransferOrder[]);
  }

  logger.info("ResponseParser", `Processed uiData: ${Object.keys(uiData).join(", ")}`);
}

/**
 * Check if a message contains approval requests.
 * Now checks uiData instead of regex patterns.
 */
export function hasApprovalRequests(_content: string, uiData?: UiPayload | null): boolean {
  return !!uiData?.approvalRequest;
}

/**
 * Extract approval requests from uiData.
 * Returns an array of ParsedApprovalOrder for InlineApprovalButtons.
 */
export interface DecisionOption {
  /** Label shown on the button, e.g. "APPROVE" */
  label: string;
  /** Normalized key sent back to orchestrator */
  key: string;
  /** Parenthetical hint, e.g. "reroute to Ohio" */
  hint: string;
  /** Colour bucket for styling */
  color: "green" | "red" | "amber" | "blue" | "zinc";
}

export interface ParsedApprovalOrder {
  orderId: string;
  product: string;
  customer: string;
  value: string;
  recommendation: string;
  options: Array<{ label: string; key: string; hint: string; color: DecisionOption["color"] }>;
}

export function extractApprovalRequests(
  _content: string,
  uiData?: UiPayload | null,
): ParsedApprovalOrder[] {
  if (!uiData?.approvalRequest) return [];
  const req = uiData.approvalRequest;
  return [
    {
      orderId: req.orderId,
      product: req.product ?? "",
      customer: req.customer ?? "",
      value: req.value ?? "",
      recommendation: req.recommendation ?? "",
      options: (req.options ?? []).map((o) => ({
        label: o.label,
        key: o.key,
        hint: o.hint ?? "",
        color: (o.key === "approve" ? "green" : o.key === "reject" ? "red" : o.key === "skip" ? "amber" : "zinc") as DecisionOption["color"],
      })),
    },
  ];
}
