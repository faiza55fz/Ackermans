import React, { Component, type ReactNode } from "react";
import { AlertTriangle, RefreshCw } from "lucide-react";

interface Props {
  children: ReactNode;
  fallbackTitle?: string;
  onReset?: () => void;
}

interface State {
  hasError: boolean;
  error: Error | null;
}

export class ErrorBoundary extends Component<Props, State> {
  constructor(props: Props) {
    super(props);
    this.state = { hasError: false, error: null };
  }

  static getDerivedStateFromError(error: Error): State {
    return { hasError: true, error };
  }

  componentDidCatch(error: Error, errorInfo: React.ErrorInfo) {
    console.error("ErrorBoundary caught an unhandled component error:", error, errorInfo);
  }

  handleRetry = () => {
    this.setState({ hasError: false, error: null });
    this.props.onReset?.();
  };

  render() {
    if (this.state.hasError) {
      return (
        <div className="p-8 my-4 bg-[#141d28] border border-[#ff7547]/40 rounded-lg text-center space-y-3">
          <AlertTriangle className="mx-auto text-[#ff7547]" size={32} />
          <h3 className="text-white text-base font-semibold">
            {this.props.fallbackTitle || "Unable to display this dashboard module"}
          </h3>
          <p className="text-xs text-[#8e9eb3] max-w-md mx-auto">
            {this.state.error?.message || "An unexpected error occurred while rendering the visualization."}
          </p>
          <div className="pt-2">
            <button
              onClick={this.handleRetry}
              className="button secondary inline-flex items-center gap-2 text-xs py-1.5 px-3"
            >
              <RefreshCw size={13} /> Retry Component
            </button>
          </div>
        </div>
      );
    }

    return this.props.children;
  }
}
