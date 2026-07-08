/**
 * Dashboard data loader — fetches facility data from DynamoDB
 * via the REST proxy's dashboard action.
 */

import { useStore } from "@/store";
import { useAuthStore } from "@/store/auth";
import { logger } from "@/lib/logger";
import { signedFetch } from "@/lib/sigv4";
import type {
  PlantId,
  FacilityStatus,
  ProductionOrder,
} from "@/types";

let API_URL: string | undefined = import.meta.env.VITE_API_URL as string | undefined;

async function getApiUrl(): Promise<string | undefined> {
  if (API_URL) return API_URL;
  try {
    const resp = await fetch("/config.json");
    if (resp.ok) {
      const config = await resp.json();
      if (config.VITE_API_URL) {
        API_URL = config.VITE_API_URL;
      }
    }
  } catch { /* config.json not found */ }
  return API_URL;
}

/**
 * Load dashboard data from DynamoDB via the REST proxy.
 * Falls back to seed data on error.
 */
export async function loadDashboardData(plant: PlantId): Promise<void> {
  const url = await getApiUrl();
  if (!url) {
    logger.info("DashboardData", "No API URL, using seed data");
    loadSeedData(plant);
    return;
  }

  try {
    let credentials = useAuthStore.getState().credentials;
    if (!credentials) {
      credentials = await useAuthStore.getState().refreshCredentials();
    }

    const resp = await signedFetch(
      url,
      {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ action: "dashboard", plant }),
      },
      credentials,
    );

    if (!resp.ok) {
      logger.info("DashboardData", `API returned ${resp.status}, falling back to seed`);
      loadSeedData(plant);
      return;
    }

    const raw = await resp.json();
    // Handle Lambda Function URL envelope
    const data = raw.body ? (typeof raw.body === "string" ? JSON.parse(raw.body) : raw.body) : raw;

    const orders: ProductionOrder[] = (data.orders || []).map((o: Record<string, unknown>) => ({
      orderId: o.order_id as string,
      plant: o.plant as string,
      productFamily: o.product_family as string,
      quantity: Number(o.quantity || 0),
      dueDate: o.due_date as string,
      customerName: (o.customer_name || "Unknown") as string,
      customerTier: (o.customer_tier || "Tier3") as string,
      orderValue: Number(o.order_value || 0),
      priority: (o.priority || null) as string | null,
      status: (o.status || "Active") as string,
    }));

    const machines = (data.machines || []).map((m: Record<string, unknown>) => ({
      machineType: m.machine_type as string,
      plant: m.plant as string,
      normalUtilizationPct: Number(m.utilization_pct_normal || 0),
      overtimeAvailablePct: Number(m.availability_pct_overtime || 0),
      weekendAvailablePct: Number(m.availability_pct_weekend || 0),
      status: (m.equipment_status === "Operational" ? "online" : "offline") as string,
    }));

    const mp = data.workforce || {};
    const workforce = {
      plant: (mp.plant as string || plant) as PlantId,
      totalOperators: Number(mp.total_operators || 0),
      allocated: Number(mp.currently_allocated || 0),
      surplus: Number(mp.available_surplus || 0),
    };

    const materials = (data.materials || []).map((m: Record<string, unknown>) => ({
      materialType: m.material_type as string,
      plant: m.plant as string,
      currentTons: Number(m.current_inventory_tons || 0),
      committedTons: Number(m.committed_to_orders_tons || 0),
      surplusTons: Number(m.available_surplus_tons || 0),
    }));

    const facilityData: FacilityStatus = { plant, orders, machines, workforce, materials };
    useStore.getState().setFacilityData(facilityData);
    logger.info("DashboardData", `Loaded ${orders.length} orders from DynamoDB for ${plant}`);
  } catch (err) {
    logger.info("DashboardData", `API error: ${err}, falling back to seed`);
    loadSeedData(plant);
  }
}

/** Fallback: load static seed data matching what's in DynamoDB. */
export function loadSeedData(plant: PlantId): void {
  const store = useStore.getState();
  const facilityData = plant === "Florida" ? buildFloridaSeed() : buildOhioSeed();
  store.setFacilityData(facilityData);
  logger.info("DashboardData", `Loaded seed data fallback for ${plant}`);
}

function buildFloridaSeed(): FacilityStatus {
  return {
    plant: "Florida",
    machines: [
      { machineType: "Rolling Mill", plant: "Florida", normalUtilizationPct: 73, overtimeAvailablePct: 12, weekendAvailablePct: 10, status: "online" },
      { machineType: "Finishing Line", plant: "Florida", normalUtilizationPct: 68, overtimeAvailablePct: 15, weekendAvailablePct: 10, status: "online" },
    ],
    workforce: { plant: "Florida", totalOperators: 42, allocated: 36, surplus: 6 },
    materials: [
      { materialType: "Hot-Rolled Coil", plant: "Florida", currentTons: 450, committedTons: 320, surplusTons: 130 },
      { materialType: "Steel Slab", plant: "Florida", currentTons: 280, committedTons: 260, surplusTons: 20 },
      { materialType: "Steel Billet", plant: "Florida", currentTons: 180, committedTons: 110, surplusTons: 70 },
    ],
    orders: [
      { orderId: "PO-2026-001", plant: "Florida", productFamily: "Steel Sheets", quantity: 500, dueDate: "2026-04-15", customerName: "Acme Manufacturing", customerTier: "Tier1", orderValue: 125000, priority: "P1", status: "Active" },
      { orderId: "PO-2026-002", plant: "Florida", productFamily: "Steel Coils", quantity: 300, dueDate: "2026-04-11", customerName: "BuildRight Corp", customerTier: "Tier1", orderValue: 98000, priority: "P1", status: "Active" },
      { orderId: "PO-2026-003", plant: "Florida", productFamily: "Steel Plates", quantity: 200, dueDate: "2026-04-14", customerName: "Metro Construction", customerTier: "Tier2", orderValue: 72000, priority: "P1", status: "Active" },
      { orderId: "PO-2026-004", plant: "Florida", productFamily: "Steel Bars", quantity: 400, dueDate: "2026-04-15", customerName: "Harbor Industries", customerTier: "Tier2", orderValue: 110000, priority: "P2", status: "Active" },
      { orderId: "PO-2026-005", plant: "Florida", productFamily: "Steel Plates", quantity: 350, dueDate: "2026-04-17", customerName: "Valley Fabrication", customerTier: "Tier2", orderValue: 88000, priority: "P2", status: "Active" },
      { orderId: "PO-2026-006", plant: "Florida", productFamily: "Steel Sheets", quantity: 250, dueDate: "2026-04-18", customerName: "SteelWorks Inc", customerTier: "Tier1", orderValue: 68000, priority: "P2", status: "Active" },
      { orderId: "PO-2026-007", plant: "Florida", productFamily: "Steel Coils", quantity: 800, dueDate: "2026-04-21", customerName: "Summit Steel", customerTier: "Tier2", orderValue: 195000, priority: "P2", status: "Active" },
      { orderId: "PO-2026-008", plant: "Florida", productFamily: "Steel Bars", quantity: 150, dueDate: "2026-04-22", customerName: "Coastal Builders", customerTier: "Tier3", orderValue: 42000, priority: "P3", status: "Active" },
      { orderId: "PO-2026-009", plant: "Florida", productFamily: "Steel Coils", quantity: 600, dueDate: "2026-04-24", customerName: "Acme Manufacturing", customerTier: "Tier1", orderValue: 156000, priority: "P2", status: "Active" },
      { orderId: "PO-2026-010", plant: "Florida", productFamily: "Steel Bars", quantity: 700, dueDate: "2026-04-28", customerName: "Midwest Metals", customerTier: "Tier3", orderValue: 175000, priority: "P3", status: "Active" },
      { orderId: "PO-2026-011", plant: "Florida", productFamily: "Steel Sheets", quantity: 450, dueDate: "2026-04-30", customerName: "Metro Construction", customerTier: "Tier2", orderValue: 115000, priority: "P3", status: "Active" },
      { orderId: "PO-2026-012", plant: "Florida", productFamily: "Steel Plates", quantity: 280, dueDate: "2026-05-04", customerName: "Pacific Steel", customerTier: "Tier3", orderValue: 78000, priority: "P3", status: "Active" },
      { orderId: "PO-2026-013", plant: "Florida", productFamily: "Steel Sheets", quantity: 900, dueDate: "2026-05-08", customerName: "BuildRight Corp", customerTier: "Tier1", orderValue: 230000, priority: "P1", status: "Active" },
      { orderId: "PO-2026-014", plant: "Florida", productFamily: "Steel Coils", quantity: 350, dueDate: "2026-05-12", customerName: "Harbor Industries", customerTier: "Tier2", orderValue: 91000, priority: "P2", status: "Active" },
      { orderId: "PO-2026-015", plant: "Florida", productFamily: "Steel Bars", quantity: 1200, dueDate: "2026-05-15", customerName: "Coastal Builders", customerTier: "Tier3", orderValue: 520000, priority: "P3", status: "Active" },
      { orderId: "PO-2026-016", plant: "Florida", productFamily: "Steel Plates", quantity: 320, dueDate: "2026-05-18", customerName: "SteelWorks Inc", customerTier: "Tier1", orderValue: 85000, priority: "P2", status: "Active" },
      { orderId: "PO-2026-017", plant: "Florida", productFamily: "Steel Coils", quantity: 550, dueDate: "2026-05-22", customerName: "Valley Fabrication", customerTier: "Tier2", orderValue: 143000, priority: "P3", status: "Active" },
      { orderId: "PO-2026-018", plant: "Florida", productFamily: "Steel Sheets", quantity: 1000, dueDate: "2026-05-28", customerName: "Summit Steel", customerTier: "Tier2", orderValue: 260000, priority: "P2", status: "Active" },
      { orderId: "PO-2026-019", plant: "Florida", productFamily: "Steel Plates", quantity: 180, dueDate: "2026-06-01", customerName: "Midwest Metals", customerTier: "Tier3", orderValue: 52000, priority: "P3", status: "Active" },
      { orderId: "PO-2026-020", plant: "Florida", productFamily: "Steel Bars", quantity: 420, dueDate: "2026-06-05", customerName: "Pacific Steel", customerTier: "Tier3", orderValue: 108000, priority: "P3", status: "Active" },
    ],
  };
}

function buildOhioSeed(): FacilityStatus {
  return {
    plant: "Ohio",
    machines: [
      { machineType: "Rolling Mill", plant: "Ohio", normalUtilizationPct: 76, overtimeAvailablePct: 12, weekendAvailablePct: 10, status: "online" },
      { machineType: "Finishing Line", plant: "Ohio", normalUtilizationPct: 71, overtimeAvailablePct: 15, weekendAvailablePct: 10, status: "online" },
    ],
    workforce: { plant: "Ohio", totalOperators: 45, allocated: 41, surplus: 4 },
    materials: [
      { materialType: "Hot-Rolled Coil", plant: "Ohio", currentTons: 500, committedTons: 420, surplusTons: 80 },
      { materialType: "Steel Slab", plant: "Ohio", currentTons: 300, committedTons: 285, surplusTons: 15 },
      { materialType: "Steel Billet", plant: "Ohio", currentTons: 200, committedTons: 155, surplusTons: 45 },
    ],
    orders: [
      { orderId: "PO-2026-021", plant: "Ohio", productFamily: "Steel Sheets", quantity: 300, dueDate: "2026-04-10", customerName: "Coastal Builders", customerTier: "Tier3", orderValue: 78000, priority: "P2", status: "Active" },
      { orderId: "PO-2026-022", plant: "Ohio", productFamily: "Steel Coils", quantity: 250, dueDate: "2026-04-12", customerName: "Midwest Metals", customerTier: "Tier3", orderValue: 65000, priority: "P3", status: "Active" },
      { orderId: "PO-2026-023", plant: "Ohio", productFamily: "Steel Bars", quantity: 180, dueDate: "2026-04-14", customerName: "Pacific Steel", customerTier: "Tier3", orderValue: 48000, priority: "P3", status: "Active" },
      { orderId: "PO-2026-024", plant: "Ohio", productFamily: "Steel Sheets", quantity: 200, dueDate: "2026-04-16", customerName: "Valley Fabrication", customerTier: "Tier2", orderValue: 52000, priority: "P2", status: "Active" },
      { orderId: "PO-2026-025", plant: "Ohio", productFamily: "Steel Coils", quantity: 280, dueDate: "2026-04-18", customerName: "Summit Steel", customerTier: "Tier2", orderValue: 72000, priority: "P2", status: "Active" },
      { orderId: "PO-2026-026", plant: "Ohio", productFamily: "Steel Sheets", quantity: 500, dueDate: "2026-04-20", customerName: "Acme Manufacturing", customerTier: "Tier1", orderValue: 130000, priority: "P1", status: "Active" },
      { orderId: "PO-2026-027", plant: "Ohio", productFamily: "Steel Coils", quantity: 400, dueDate: "2026-04-22", customerName: "SteelWorks Inc", customerTier: "Tier1", orderValue: 104000, priority: "P1", status: "Active" },
      { orderId: "PO-2026-028", plant: "Ohio", productFamily: "Steel Bars", quantity: 350, dueDate: "2026-04-24", customerName: "BuildRight Corp", customerTier: "Tier1", orderValue: 91000, priority: "P1", status: "Active" },
      { orderId: "PO-2026-029", plant: "Ohio", productFamily: "Steel Sheets", quantity: 280, dueDate: "2026-04-28", customerName: "Harbor Industries", customerTier: "Tier2", orderValue: 73000, priority: "P2", status: "Active" },
      { orderId: "PO-2026-030", plant: "Ohio", productFamily: "Steel Coils", quantity: 900, dueDate: "2026-04-30", customerName: "Metro Construction", customerTier: "Tier2", orderValue: 234000, priority: "P1", status: "Active" },
      { orderId: "PO-2026-031", plant: "Ohio", productFamily: "Steel Bars", quantity: 220, dueDate: "2026-05-04", customerName: "Valley Fabrication", customerTier: "Tier2", orderValue: 57000, priority: "P2", status: "Active" },
      { orderId: "PO-2026-032", plant: "Ohio", productFamily: "Steel Sheets", quantity: 380, dueDate: "2026-05-08", customerName: "Coastal Builders", customerTier: "Tier3", orderValue: 99000, priority: "P3", status: "Active" },
      { orderId: "PO-2026-033", plant: "Ohio", productFamily: "Steel Coils", quantity: 320, dueDate: "2026-05-12", customerName: "Metro Construction", customerTier: "Tier2", orderValue: 83000, priority: "P2", status: "Active" },
      { orderId: "PO-2026-034", plant: "Ohio", productFamily: "Steel Bars", quantity: 750, dueDate: "2026-05-15", customerName: "Midwest Metals", customerTier: "Tier3", orderValue: 195000, priority: "P3", status: "Active" },
      { orderId: "PO-2026-035", plant: "Ohio", productFamily: "Steel Sheets", quantity: 260, dueDate: "2026-05-18", customerName: "Pacific Steel", customerTier: "Tier3", orderValue: 68000, priority: "P3", status: "Active" },
      { orderId: "PO-2026-036", plant: "Ohio", productFamily: "Steel Coils", quantity: 450, dueDate: "2026-05-22", customerName: "Acme Manufacturing", customerTier: "Tier1", orderValue: 117000, priority: "P1", status: "Active" },
      { orderId: "PO-2026-037", plant: "Ohio", productFamily: "Steel Bars", quantity: 200, dueDate: "2026-05-25", customerName: "BuildRight Corp", customerTier: "Tier1", orderValue: 52000, priority: "P2", status: "Active" },
      { orderId: "PO-2026-038", plant: "Ohio", productFamily: "Steel Sheets", quantity: 340, dueDate: "2026-05-28", customerName: "Harbor Industries", customerTier: "Tier2", orderValue: 88000, priority: "P2", status: "Active" },
      { orderId: "PO-2026-039", plant: "Ohio", productFamily: "Steel Coils", quantity: 380, dueDate: "2026-06-01", customerName: "SteelWorks Inc", customerTier: "Tier1", orderValue: 99000, priority: "P1", status: "Active" },
      { orderId: "PO-2026-040", plant: "Ohio", productFamily: "Steel Bars", quantity: 160, dueDate: "2026-06-05", customerName: "Summit Steel", customerTier: "Tier2", orderValue: 42000, priority: "P3", status: "Active" },
    ],
  };
}


/**
 * Apply a transfer acceptance to facility data.
 * Updates sender plant orders to "Transferred" status and adds order to receiver's list.
 */
export function applyTransferToFacilityData(
  facilityData: import("@/types").FacilityStatus | null,
  transfer: import("@/types").TransferRequest,
  receiverPlant: import("@/types").PlantId,
): import("@/types").FacilityStatus | null {
  if (!facilityData) return null;

  // If this is the sender's facility, mark order as transferred
  if (facilityData.plant === transfer.order.plant) {
    return {
      ...facilityData,
      orders: facilityData.orders.map((o) =>
        o.orderId === transfer.orderId
          ? { ...o, status: `Transferred to ${receiverPlant}` }
          : o,
      ),
    };
  }

  // If this is the receiver's facility, add the transferred order
  if (facilityData.plant === receiverPlant) {
    const exists = facilityData.orders.some((o) => o.orderId === transfer.orderId);
    if (exists) return facilityData;
    return {
      ...facilityData,
      orders: [
        ...facilityData.orders,
        {
          ...transfer.order,
          plant: receiverPlant,
          status: "Active",
          transferredFrom: transfer.order.plant,
        },
      ],
    };
  }

  return facilityData;
}
