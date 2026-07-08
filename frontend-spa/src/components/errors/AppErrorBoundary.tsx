import { Component, type ReactNode, type ErrorInfo } from "react";
import { logger } from "@/lib/logger";

interface Props {
  children: ReactNode;
}

interface State {
  hasError: boolean;
}

export class AppErrorBoundary extends Component<Props, State> {
  state: State = { hasError: false };

  static getDerivedStateFromError(): State {
    return { hasError: true };
  }

  componentDidCatch(error: Error, info: ErrorInfo) {
    logger.error("ErrorBoundary", `App crashed: ${error.message}`, info.componentStack);
  }

  render() {
    if (this.state.hasError) {
      return (
        <div className="flex h-screen items-center justify-center bg-gray-50 text-gray-900">
          <div className="text-center space-y-3">
            <p className="text-lg font-medium">Something went wrong</p>
            <p className="text-sm text-gray-500">The application encountered an unexpected error.</p>
            <button
              className="min-h-11 rounded-lg bg-blue-600 px-4 py-2 text-sm text-white hover:bg-blue-500"
              onClick={() => window.location.reload()}
            >
              Reload
            </button>
          </div>
        </div>
      );
    }
    return this.props.children;
  }
}
