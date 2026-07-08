import { useEffect, useState } from "react";
import { useStore } from "@/store";
import { JobStatusView } from "./JobStatusView";
import { EfficiencyView } from "./EfficiencyView";
import { loadDashboardData } from "@/lib/dashboardData";
import { ClipboardList, Activity } from "lucide-react";

export function DashboardPage() {
  const planner = useStore((s) => s.planner);
  const dashboardView = useStore((s) => s.dashboardView);
  const setDashboardView = useStore((s) => s.setDashboardView);
  const facilityData = useStore((s) => s.facilityData);

  useEffect(() => {
    if (planner && !facilityData) {
      loadDashboardData(planner.plant);
    }
  }, [planner, facilityData]);

  if (!planner) {
    return <PlantSelector />;
  }

  return (
    <div data-testid="dashboard-page" className="flex flex-1 flex-col overflow-hidden bg-slate-950">
      <div className="flex-1 overflow-y-auto scrollbar-thin">
        <div className="mx-auto max-w-7xl p-6 lg:p-8">

          <div className="mb-6">
            <h2 className="text-xl font-semibold text-slate-100 tracking-tight">
              {planner.displayName} Plant Operations
            </h2>
            <p className="text-sm text-slate-500">
              Real-time production monitoring and capacity management
            </p>
          </div>

          {/* Tab navigation */}
          <div className="mb-6 glass-card overflow-hidden">
            <div className="border-b border-white/[0.06] px-5">
              <nav className="flex gap-1">
                <button
                  onClick={() => setDashboardView("jobs")}
                  className={`flex items-center gap-2 border-b-2 px-3 py-3.5 text-[13px] font-medium transition-all duration-200 ${
                    dashboardView === "jobs"
                      ? "border-cyan-500 text-cyan-400"
                      : "border-transparent text-slate-500 hover:text-slate-300"
                  }`}
                  data-testid="dashboard-tab-jobs"
                >
                  <ClipboardList size={15} />
                  Job Status Tracking
                </button>
                <button
                  onClick={() => setDashboardView("efficiency")}
                  className={`flex items-center gap-2 border-b-2 px-3 py-3.5 text-[13px] font-medium transition-all duration-200 ${
                    dashboardView === "efficiency"
                      ? "border-cyan-500 text-cyan-400"
                      : "border-transparent text-slate-500 hover:text-slate-300"
                  }`}
                  data-testid="dashboard-tab-efficiency"
                >
                  <Activity size={15} />
                  Operational Efficiency
                </button>
              </nav>
            </div>
            <div className="p-6">
              {dashboardView === "jobs" ? <JobStatusView /> : <EfficiencyView />}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

function PlantSelector() {
  const setPlanner = useStore((s) => s.setPlanner);
  const [hoveredPlant, setHoveredPlant] = useState<"Florida" | "Ohio" | null>(null);

  function select(plant: "Florida" | "Ohio") {
    const displayName = plant === "Florida" ? "Miami" : "Ohio";
    setPlanner({ plant, displayName });
  }

  // Approximate SVG coordinates for a zoomed eastern-US view
  const plants = [
    { id: "Florida" as const, label: "Miami Plant", sub: "Florida", x: 520, y: 520, color: "#f59e0b", glow: "#f59e0b40" },
    { id: "Ohio" as const, label: "Ohio Plant", sub: "Columbus, OH", x: 480, y: 240, color: "#06b6d4", glow: "#06b6d440" },
  ];

  return (
    <div className="flex flex-1 flex-col items-center justify-center bg-slate-950 p-8 overflow-hidden relative">
      {/* Subtle grid background */}
      <div className="absolute inset-0 opacity-[0.03]" style={{
        backgroundImage: "linear-gradient(rgba(255,255,255,.1) 1px, transparent 1px), linear-gradient(90deg, rgba(255,255,255,.1) 1px, transparent 1px)",
        backgroundSize: "40px 40px",
      }} />

      <div className="text-center mb-6 relative z-10">
        <h2 className="text-2xl font-semibold text-slate-100 tracking-tight">Select Your Facility</h2>
        <p className="mt-2 text-sm text-slate-500">Click a plant location on the map</p>
      </div>

      <div className="relative z-10 w-full max-w-2xl">
        <svg viewBox="200 100 500 500" className="w-full h-auto drop-shadow-2xl">
          {/* Simplified eastern US outline */}
          <path
            d="M300,130 L520,130 L540,150 L560,160 L570,200 L560,240 L550,280 L540,300 L530,340 L540,360 L550,380 L560,400 L550,420 L540,440 L530,460 L540,480 L550,500 L540,520 L520,540 L500,560 L480,570 L460,560 L440,540 L420,520 L400,500 L380,480 L360,460 L340,440 L320,420 L300,400 L280,380 L270,360 L260,340 L250,300 L260,260 L270,220 L280,180 L290,150 Z"
            fill="rgba(255,255,255,0.02)"
            stroke="rgba(255,255,255,0.08)"
            strokeWidth="1.5"
          />
          {/* State divider hint */}
          <path d="M260,320 L560,320" stroke="rgba(255,255,255,0.04)" strokeWidth="1" strokeDasharray="4,4" />

          {/* Connection line between plants */}
          <line x1={plants[0]!.x} y1={plants[0]!.y} x2={plants[1]!.x} y2={plants[1]!.y}
            stroke="rgba(255,255,255,0.06)" strokeWidth="1.5" strokeDasharray="6,6" />

          {/* Plant markers */}
          {plants.map((p) => {
            const isHovered = hoveredPlant === p.id;
            const scale = isHovered ? 1.15 : 1;
            return (
              <g
                key={p.id}
                onClick={() => select(p.id)}
                onMouseEnter={() => setHoveredPlant(p.id)}
                onMouseLeave={() => setHoveredPlant(null)}
                className="cursor-pointer"
                style={{ transition: "transform 0.2s ease" }}
              >
                {/* Pulse ring */}
                <circle cx={p.x} cy={p.y} r={isHovered ? 38 : 30} fill="none" stroke={p.color} strokeWidth="1.5" opacity={isHovered ? 0.5 : 0.2}>
                  <animate attributeName="r" values={isHovered ? "30;42;30" : "24;32;24"} dur="2.5s" repeatCount="indefinite" />
                  <animate attributeName="opacity" values={isHovered ? "0.5;0;0.5" : "0.2;0;0.2"} dur="2.5s" repeatCount="indefinite" />
                </circle>
                {/* Glow */}
                <circle cx={p.x} cy={p.y} r={isHovered ? 28 : 22} fill={p.glow} opacity={isHovered ? 0.6 : 0.3} />
                {/* Pin body */}
                <circle cx={p.x} cy={p.y} r={isHovered ? 18 : 14} fill={p.color} opacity={0.9}
                  style={{ transform: `scale(${scale})`, transformOrigin: `${p.x}px ${p.y}px`, transition: "transform 0.2s ease" }} />
                {/* Inner dot */}
                <circle cx={p.x} cy={p.y} r={5} fill="white" opacity={0.9} />
                {/* Label */}
                <text x={p.x} y={p.y - 28} textAnchor="middle" fill="white" fontSize="14" fontWeight="600" opacity={isHovered ? 1 : 0.85}>
                  {p.label}
                </text>
                <text x={p.x} y={p.y - 14} textAnchor="middle" fill="rgba(255,255,255,0.5)" fontSize="10">
                  {p.sub}
                </text>
              </g>
            );
          })}
        </svg>
      </div>

      {/* Hover hint */}
      <p className="mt-4 text-xs text-slate-600 relative z-10">
        {hoveredPlant ? `Click to enter ${hoveredPlant === "Florida" ? "Miami" : "Ohio"} operations` : "Hover over a pin to select"}
      </p>
    </div>
  );
}
