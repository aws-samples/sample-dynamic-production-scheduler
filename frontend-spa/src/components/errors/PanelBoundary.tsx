import { Component, type ReactNode, type ErrorInfo } from "react";
import { logger } from "@/lib/logger";

interface Props {
  children: ReactNode;
  name: string;
}

interface State {
  hasError: boolean;
}

export class PanelBoundary extends Component<Props, State> {
  state: State = { hasError: false };

  static getDerivedStateFromError(): State {
    return { hasError: true };
  }

  componentDidCatch(error: Error, info: ErrorInfo) {
    logger.error("ErrorBoundary", `${this.props.name} crashed: ${error.message}`, info.componentStack);
  }

  render() {
    if (this.state.hasError) {
      return (
        <div className="flex flex-1 items-center justify-center p-4">
          <div className="text-center space-y-2">
            <p className="text-sm text-gray-500">This panel encountered an error.</p>
            <button
              className="min-h-11 rounded-lg bg-gray-100 px-3 py-1.5 text-xs text-gray-600 hover:bg-zinc-700"
              onClick={() => this.setState({ hasError: false })}
            >
              Retry
            </button>
          </div>
        </div>
      );
    }
    return this.props.children;
  }
}
