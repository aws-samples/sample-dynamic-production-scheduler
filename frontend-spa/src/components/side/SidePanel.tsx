import { useStore } from "@/store";
import { SidePanelBoundary } from "@/components/errors/SidePanelBoundary";
import { PhaseProgressBar } from "./PhaseProgressBar";
import { PanelContent } from "./PanelContent";
import { AuditTrailSection } from "./AuditTrailSection";
import type { SidePanelMode } from "@/types";
import { BarChart3, Users, ClipboardList, Eye } from "lucide-react";

const TABS: { mode: SidePanelMode; label: string; icon: typeof BarChart3 }[] = [
  { mode: "tracker", label: "Tracker", icon: BarChart3 },
  { mode: "agents", label: "Agents", icon: Users },
  { mode: "orders", label: "Orders", icon: ClipboardList },
  { mode: "visualizations", label: "Visuals", icon: Eye },
];

export function SidePanel() {
  const mode = useStore((s) => s.sidePanel.mode);
  const setSidePanelMode = useStore((s) => s.setSidePanelMode);

  // Don't show tabs when in approval or detail mode (those are triggered by events)
  const showTabs = mode !== "approval" && mode !== "detail";

  return (
    <SidePanelBoundary>
      <div className="flex h-full flex-col">
        <PhaseProgressBar />
        {showTabs && (
          <div className="flex border-b border-slate-700 bg-slate-800">
            {TABS.map((tab) => {
              const Icon = tab.icon;
              const active = mode === tab.mode;
              return (
                <button
                  key={tab.mode}
                  type="button"
                  onClick={() => setSidePanelMode(tab.mode)}
                  className={`flex-1 flex items-center justify-center gap-1 px-2 py-2 text-xs transition-colors ${
                    active
                      ? "border-b-2 border-blue-400 text-blue-400 bg-slate-750"
                      : "text-slate-400 hover:text-slate-200 hover:bg-slate-750"
                  }`}
                  data-testid={`tab-${tab.mode}`}
                >
                  <Icon size={12} />
                  {tab.label}
                </button>
              );
            })}
          </div>
        )}
        <div className="flex-1 overflow-y-auto">
          <PanelContent />
        </div>
        <AuditTrailSection />
      </div>
    </SidePanelBoundary>
  );
}
