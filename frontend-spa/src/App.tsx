import { useEffect } from "react";
import { AppHeader } from "@/components/AppHeader";
import { MainLayout } from "@/components/MainLayout";
import { ChatPanel } from "@/components/chat/ChatPanel";
import { SidePanel } from "@/components/side/SidePanel";
import { DashboardPage } from "@/components/dashboard/DashboardPage";
import { TransferDashboardPage } from "@/components/dashboard/TransferDashboardPage";
import { TransferNegotiationView } from "@/components/transfers/TransferNegotiationView";
import { DisruptionPage } from "@/components/disruption/DisruptionPage";
import { AppErrorBoundary } from "@/components/errors/AppErrorBoundary";
import { LoginPage } from "@/components/auth/LoginPage";
import { useAuthStore } from "@/store/auth";
import { useStore } from "@/store";
import { connect, disconnect } from "@/lib/streaming";

export default function App() {
  const { user, loading, initialize } = useAuthStore();
  const currentView = useStore((s) => s.currentView);

  useEffect(() => {
    initialize();
  }, [initialize]);

  useEffect(() => {
    if (user) {
      connect();
      return () => disconnect();
    }
  }, [user]);

  if (loading) {
    return (
      <div className="flex h-screen items-center justify-center bg-gray-50">
        <p className="text-gray-500">Loading...</p>
      </div>
    );
  }

  if (!user) {
    return <LoginPage />;
  }

  return (
    <AppErrorBoundary>
      <div className="flex h-screen flex-col bg-gray-50 text-gray-900">
        <AppHeader />
        {currentView === "dashboard" && <DashboardPage />}
        {currentView === "disruption" && <DisruptionPage />}
        {currentView === "chat" && (
          <MainLayout
            chat={<ChatPanel />}
            sidePanel={<SidePanel />}
          />
        )}
        {currentView === "transfers" && <TransferNegotiationView />}
        {currentView === "transfer-dashboard" && <TransferDashboardPage />}
      </div>
    </AppErrorBoundary>
  );
}
