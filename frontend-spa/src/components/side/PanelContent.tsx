import { lazy, Suspense } from "react";
import { useStore } from "@/store";
import { CapacityTracker } from "./CapacityTracker";
import { ApprovalCard } from "./ApprovalCard";
import { SubAgentStatus } from "./SubAgentStatus";
import { OrderHistory } from "./OrderHistory";

const DataDetailView = lazy(() =>
  import("./DataDetailView").then((m) => ({ default: m.DataDetailView })),
);

const CascadeImpactView = lazy(() =>
  import("@/components/visualizations/CascadeImpactView").then((m) => ({
    default: m.CascadeImpactView,
  })),
);

const ScorecardView = lazy(() =>
  import("@/components/visualizations/ScorecardView").then((m) => ({
    default: m.ScorecardView,
  })),
);

const TransferFlowView = lazy(() =>
  import("@/components/visualizations/TransferFlowView").then((m) => ({
    default: m.TransferFlowView,
  })),
);

const Loading = () => (
  <div className="p-4 text-sm text-gray-400">Loading...</div>
);

export function PanelContent() {
  const mode = useStore((s) => s.sidePanel.mode);

  if (mode === "approval") return <ApprovalCard />;

  if (mode === "detail") {
    return (
      <Suspense fallback={<Loading />}>
        <DataDetailView />
      </Suspense>
    );
  }

  if (mode === "agents") return <SubAgentStatus />;
  if (mode === "orders") return <OrderHistory />;

  if (mode === "visualizations") {
    return (
      <Suspense fallback={<Loading />}>
        <div className="space-y-4">
          <CascadeImpactView />
          <ScorecardView />
          <TransferFlowView />
        </div>
      </Suspense>
    );
  }

  // Default: tracker
  return <CapacityTracker />;
}
