import { useState, type ReactNode } from "react";
import { PanelRightOpen, PanelRightClose } from "lucide-react";

interface MainLayoutProps {
  chat: ReactNode;
  sidePanel: ReactNode;
}

export function MainLayout({ chat, sidePanel }: MainLayoutProps) {
  const [sidePanelOpen, setSidePanelOpen] = useState(true);

  return (
    <div className="flex flex-1 overflow-hidden">
      <main className="flex flex-1 flex-col overflow-hidden">{chat}</main>

      <button
        type="button"
        onClick={() => setSidePanelOpen((v) => !v)}
        className="fixed right-2 top-14 z-20 rounded bg-slate-800 p-1.5 text-slate-400 hover:text-slate-200 lg:hidden"
        data-testid="side-panel-toggle"
        aria-label={sidePanelOpen ? "Close side panel" : "Open side panel"}
      >
        {sidePanelOpen ? <PanelRightClose size={16} /> : <PanelRightOpen size={16} />}
      </button>

      <aside
        className={`shrink-0 border-l border-white/[0.08] overflow-y-auto transition-all duration-300 bg-slate-800 ${
          sidePanelOpen
            ? "w-[340px] xl:w-[400px]"
            : "w-0 overflow-hidden border-l-0"
        }`}
      >
        {sidePanelOpen && sidePanel}
      </aside>
    </div>
  );
}
