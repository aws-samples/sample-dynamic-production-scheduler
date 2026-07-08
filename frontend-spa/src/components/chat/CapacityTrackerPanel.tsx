import { useEffect, useState } from "react";
import { useStore } from "@/store";
import { useAuthStore } from "@/store/auth";
import { signedFetch } from "@/lib/sigv4";
import { Factory, Users, Package, TrendingDown, CheckCircle, XCircle, Clock } from "lucide-react";

interface TrackerData {
  session_id: string;
  rolling_mill_normal_hrs: number;
  rolling_mill_overtime_hrs: number;
  rolling_mill_weekend_hrs: number;
  finishing_line_normal_hrs: number;
  finishing_line_overtime_hrs: number;
  finishing_line_weekend_hrs: number;
  material_surplus_tons: Record<string, number>;
  workforce_surplus: number;
  orders_transferred: string[];
  orders_delayed: string[];
  orders_rejected: string[];
  last_updated: string;
}

export function CapacityTrackerPanel() {
  const [tracker, setTracker] = useState<TrackerData | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const sessionId = useStore((s) => s.session.sessionId);

  useEffect(() => {
    if (!sessionId || sessionId.length < 10) return;

    const fetchTracker = async () => {
      if (!sessionId || sessionId.length < 10) return;
      setLoading(true);
      setError(null);
      try {
        const apiUrl = import.meta.env.VITE_API_URL || "/api";
        let credentials = useAuthStore.getState().credentials;
        if (!credentials) {
          credentials = await useAuthStore.getState().refreshCredentials();
        }
        const response = await signedFetch(
          apiUrl,
          {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ 
              action: "tracker",
              sessionId 
            }),
          },
          credentials,
        );
        
        if (response.status === 404 || response.status === 400) {
          // Tracker doesn't exist yet or action not supported - normal
          setTracker(null);
          setError(null);
          setLoading(false);
          return;
        }
        
        if (!response.ok) {
          throw new Error("Failed to fetch tracker data");
        }
        
        const data = await response.json();
        setTracker(data);
      } catch (err) {
        setError(err instanceof Error ? err.message : "Unknown error");
      } finally {
        setLoading(false);
      }
    };

    fetchTracker();
    const interval = setInterval(fetchTracker, 5000); // Poll every 5 seconds
    return () => clearInterval(interval);
  }, [sessionId]);

  if (!sessionId) return null;
  if (loading && !tracker) {
    return (
      <div className="rounded-xl border border-white/[0.06] bg-slate-800/80 p-4">
        <p className="text-sm text-slate-400">Loading capacity tracker...</p>
      </div>
    );
  }
  if (error) {
    return (
      <div className="rounded-xl border border-red-500/20 bg-red-500/10 p-4">
        <p className="text-sm text-red-400">Error: {error}</p>
      </div>
    );
  }
  if (!tracker) return null;

  const totalRM = tracker.rolling_mill_normal_hrs + tracker.rolling_mill_overtime_hrs + tracker.rolling_mill_weekend_hrs;
  const totalFL = tracker.finishing_line_normal_hrs + tracker.finishing_line_overtime_hrs + tracker.finishing_line_weekend_hrs;
  const totalOrders = tracker.orders_transferred.length + tracker.orders_delayed.length + tracker.orders_rejected.length;

  return (
    <div className="rounded-xl border border-white/[0.06] bg-slate-800/80 p-4 space-y-4">
      <div className="flex items-center justify-between">
        <h3 className="text-sm font-semibold text-slate-100">Capacity Tracker</h3>
        <span className="text-xs text-slate-500">
          Updated {new Date(tracker.last_updated).toLocaleTimeString()}
        </span>
      </div>

      {/* Machine Capacity */}
      <div className="space-y-3">
        <div>
          <div className="flex items-center justify-between mb-1">
            <div className="flex items-center gap-2">
              <Factory size={14} className="text-blue-400" />
              <span className="text-xs font-medium text-slate-300">Rolling Mill</span>
            </div>
            <span className="text-xs font-semibold text-blue-400">{totalRM.toFixed(1)} hrs</span>
          </div>
          <div className="h-2 bg-slate-700 rounded-full overflow-hidden">
            <div
              className="h-full bg-gradient-to-r from-blue-500 to-blue-400 transition-all duration-500"
              style={{ width: `${Math.min((totalRM / 200) * 100, 100)}%` }}
            />
          </div>
          <div className="flex gap-2 mt-1 text-[10px] text-slate-500">
            <span>Normal: {tracker.rolling_mill_normal_hrs.toFixed(1)}</span>
            <span>OT: {tracker.rolling_mill_overtime_hrs.toFixed(1)}</span>
            <span>Wknd: {tracker.rolling_mill_weekend_hrs.toFixed(1)}</span>
          </div>
        </div>

        <div>
          <div className="flex items-center justify-between mb-1">
            <div className="flex items-center gap-2">
              <Factory size={14} className="text-purple-400" />
              <span className="text-xs font-medium text-slate-300">Finishing Line</span>
            </div>
            <span className="text-xs font-semibold text-purple-400">{totalFL.toFixed(1)} hrs</span>
          </div>
          <div className="h-2 bg-slate-700 rounded-full overflow-hidden">
            <div
              className="h-full bg-gradient-to-r from-purple-500 to-purple-400 transition-all duration-500"
              style={{ width: `${Math.min((totalFL / 120) * 100, 100)}%` }}
            />
          </div>
          <div className="flex gap-2 mt-1 text-[10px] text-slate-500">
            <span>Normal: {tracker.finishing_line_normal_hrs.toFixed(1)}</span>
            <span>OT: {tracker.finishing_line_overtime_hrs.toFixed(1)}</span>
            <span>Wknd: {tracker.finishing_line_weekend_hrs.toFixed(1)}</span>
          </div>
        </div>
      </div>

      {/* Materials */}
      {Object.keys(tracker.material_surplus_tons).length > 0 && (
        <div>
          <div className="flex items-center gap-2 mb-2">
            <Package size={14} className="text-amber-400" />
            <span className="text-xs font-medium text-slate-300">Materials</span>
          </div>
          <div className="space-y-1">
            {Object.entries(tracker.material_surplus_tons).map(([material, tons]) => (
              <div key={material} className="flex items-center justify-between text-xs">
                <span className="text-slate-400">{material}</span>
                <span className="font-medium text-amber-400">{tons.toFixed(1)} tons</span>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Workforce */}
      <div>
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Users size={14} className="text-emerald-400" />
            <span className="text-xs font-medium text-slate-300">Workforce</span>
          </div>
          <span className="text-xs font-semibold text-emerald-400">{tracker.workforce_surplus} operators</span>
        </div>
      </div>

      {/* Order Decisions */}
      {totalOrders > 0 && (
        <div className="pt-3 border-t border-white/[0.06]">
          <div className="flex items-center gap-2 mb-2">
            <TrendingDown size={14} className="text-cyan-400" />
            <span className="text-xs font-medium text-slate-300">Order Decisions</span>
          </div>
          <div className="grid grid-cols-3 gap-2">
            <div className="flex items-center gap-1.5 rounded-lg bg-emerald-500/10 px-2 py-1.5">
              <CheckCircle size={12} className="text-emerald-400" />
              <span className="text-xs font-semibold text-emerald-400">{tracker.orders_transferred.length}</span>
            </div>
            <div className="flex items-center gap-1.5 rounded-lg bg-yellow-500/10 px-2 py-1.5">
              <Clock size={12} className="text-yellow-400" />
              <span className="text-xs font-semibold text-yellow-400">{tracker.orders_delayed.length}</span>
            </div>
            <div className="flex items-center gap-1.5 rounded-lg bg-red-500/10 px-2 py-1.5">
              <XCircle size={12} className="text-red-400" />
              <span className="text-xs font-semibold text-red-400">{tracker.orders_rejected.length}</span>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
