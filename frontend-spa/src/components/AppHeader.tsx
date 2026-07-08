import { useAuthStore } from "@/store/auth";
import { useStore } from "@/store";
import type { AppView, PlantId } from "@/types";
import { PLANT_DISPLAY_NAMES } from "@/types";
import { LayoutDashboard, MessageSquare, ArrowLeftRight, Bell, LogOut, ChevronDown, AlertTriangle, Factory, BarChart3 } from "lucide-react";
import { useState, useRef, useEffect } from "react";

const NAV_ITEMS: { view: AppView; label: string; icon: typeof LayoutDashboard; testId: string }[] = [
  { view: "dashboard", label: "Dashboard", icon: LayoutDashboard, testId: "nav-dashboard" },
  { view: "disruption", label: "Disruption", icon: AlertTriangle, testId: "nav-disruption" },
  { view: "chat", label: "AI Assistant", icon: MessageSquare, testId: "nav-chat" },
  { view: "transfers", label: "Transfers", icon: ArrowLeftRight, testId: "nav-transfers" },
  { view: "transfer-dashboard", label: "Transfer Dashboard", icon: BarChart3, testId: "nav-transfer-dashboard" },
];

export function AppHeader() {
  const { user, logout } = useAuthStore();
  const planner = useStore((s) => s.planner);
  const setPlanner = useStore((s) => s.setPlanner);
  const setFacilityData = useStore((s) => s.setFacilityData);
  const currentView = useStore((s) => s.currentView);
  const setCurrentView = useStore((s) => s.setCurrentView);
  const unackedCount = useStore((s) =>
    s.notifications.filter((n) => !n.acknowledged && n.plant === planner?.plant).length,
  );

  const [plantMenuOpen, setPlantMenuOpen] = useState(false);
  const menuRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    function handleClick(e: MouseEvent) {
      if (menuRef.current && !menuRef.current.contains(e.target as Node)) {
        setPlantMenuOpen(false);
      }
    }
    document.addEventListener("mousedown", handleClick);
    return () => document.removeEventListener("mousedown", handleClick);
  }, []);

  function switchPlant(plant: PlantId) {
    setPlanner({ plant, displayName: PLANT_DISPLAY_NAMES[plant] });
    setFacilityData(null as never);
    setPlantMenuOpen(false);
  }

  return (
    <header className="sticky top-0 z-30 flex h-[10vh] shrink-0 items-center justify-between border-b border-white/[0.06] bg-slate-900/95 backdrop-blur-md px-5">
      <div className="flex items-center gap-5">
        {/* Logo */}
        <div className="flex items-center gap-2.5">
          <div className="flex h-[5vh] w-[5vh] items-center justify-center rounded-lg bg-gradient-to-br from-cyan-500 to-teal-500 shadow-lg shadow-cyan-500/20">
            <Factory size={24} className="text-white" />
          </div>
          <div>
            <h1 className="text-[1.8vh] font-semibold text-slate-100 tracking-tight">DisruptionAI</h1>
            {planner && (
              <div className="relative" ref={menuRef}>
                <button
                  onClick={() => setPlantMenuOpen(!plantMenuOpen)}
                  className="flex items-center gap-1 text-[1.3vh] text-slate-400 hover:text-cyan-400 transition-colors duration-200"
                  data-testid="plant-switcher"
                >
                  {planner.displayName} Plant
                  <ChevronDown size={12} />
                </button>
                {plantMenuOpen && (
                  <div className="absolute left-0 top-full mt-2 w-48 rounded-xl border border-white/[0.08] bg-slate-800 py-1.5 shadow-xl shadow-black/40 z-50">
                    {(["Florida", "Ohio"] as PlantId[]).map((p) => (
                      <button
                        key={p}
                        onClick={() => switchPlant(p)}
                        className={`flex w-full items-center gap-2.5 px-3.5 py-2 text-sm transition-all duration-200 ${
                          planner.plant === p
                            ? "bg-cyan-500/10 text-cyan-400"
                            : "text-slate-300 hover:bg-white/[0.04] hover:text-slate-100"
                        }`}
                        data-testid={`switch-plant-${p.toLowerCase()}`}
                      >
                        <span className="text-xs">{p === "Florida" ? "🌴" : "🏭"}</span>
                        {PLANT_DISPLAY_NAMES[p]} Plant
                        {planner.plant === p && <span className="ml-auto text-cyan-500 text-xs">✓</span>}
                      </button>
                    ))}
                  </div>
                )}
              </div>
            )}
          </div>
        </div>

        {/* Nav */}
        <nav className="ml-2 flex gap-0.5 border-l border-white/[0.06] pl-4" aria-label="Main navigation">
          {NAV_ITEMS.map(({ view, label, icon: Icon, testId }) => (
            <button
              key={view}
              onClick={() => setCurrentView(view)}
              className={`group flex items-center gap-2 rounded-lg px-3 py-[1.5vh] text-[1.5vh] font-medium transition-all duration-200 ${
                currentView === view
                  ? "bg-cyan-500/10 text-cyan-400 shadow-sm shadow-cyan-500/10"
                  : "text-slate-400 hover:bg-white/[0.04] hover:text-slate-200"
              }`}
              data-testid={testId}
              aria-current={currentView === view ? "page" : undefined}
            >
              <Icon size={18} className={currentView === view ? "text-cyan-400" : "text-slate-500 group-hover:text-slate-300 transition-colors"} />
              {label}
            </button>
          ))}
        </nav>
      </div>

      {/* Right side */}
      <div className="flex items-center gap-2">
        <button
          className="relative rounded-lg p-2 text-slate-400 hover:bg-white/[0.04] hover:text-slate-200 transition-all duration-200"
          aria-label="Notifications"
        >
          <Bell size={20} />
          {unackedCount > 0 && (
            <span className="absolute right-1 top-1 flex h-[2vh] w-[2vh] items-center justify-center rounded-full bg-red-500 text-[1vh] font-bold text-white ring-2 ring-slate-900">
              {unackedCount}
            </span>
          )}
        </button>
        {user && (
          <div className="flex items-center gap-2.5 border-l border-white/[0.06] pl-3 ml-1">
            <div className="flex h-[4vh] w-[4vh] items-center justify-center rounded-full bg-gradient-to-br from-cyan-500/20 to-teal-500/20 ring-1 ring-cyan-500/30">
              <span className="text-[1.5vh] font-semibold text-cyan-400">
                {user.email.charAt(0).toUpperCase()}
              </span>
            </div>
            <p className="hidden sm:block text-[1.5vh] text-slate-300" data-testid="user-email">{user.email}</p>
            <button
              onClick={logout}
              className="rounded-lg p-1.5 text-slate-500 hover:bg-white/[0.04] hover:text-slate-300 transition-all duration-200"
              data-testid="logout-button"
              aria-label="Sign out"
            >
              <LogOut size={18} />
            </button>
          </div>
        )}
      </div>
    </header>
  );
}
