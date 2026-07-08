import type { ReactNode } from "react";
import { PanelBoundary } from "./PanelBoundary";

export function SidePanelBoundary({ children }: { children: ReactNode }) {
  return <PanelBoundary name="SidePanel">{children}</PanelBoundary>;
}
