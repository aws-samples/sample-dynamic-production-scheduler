import type { ReactNode } from "react";
import { PanelBoundary } from "./PanelBoundary";

export function ChatPanelBoundary({ children }: { children: ReactNode }) {
  return <PanelBoundary name="ChatPanel">{children}</PanelBoundary>;
}
