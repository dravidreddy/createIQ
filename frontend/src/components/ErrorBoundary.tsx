import React, { Component, ErrorInfo, ReactNode } from 'react';
import { AlertTriangle, RefreshCcw } from 'lucide-react';

interface Props {
  children?: ReactNode;
}

interface State {
  hasError: boolean;
  error: Error | null;
  errorInfo: ErrorInfo | null;
}

export class ErrorBoundary extends Component<Props, State> {
  public state: State = {
    hasError: false,
    error: null,
    errorInfo: null
  };

  public static getDerivedStateFromError(error: Error): State {
    return { hasError: true, error, errorInfo: null };
  }

  public componentDidCatch(error: Error, errorInfo: ErrorInfo) {
    console.error('Uncaught error:', error, errorInfo);
    this.setState({ errorInfo });
  }

  private handleReset = () => {
    this.setState({ hasError: false, error: null, errorInfo: null });
    window.location.reload();
  };

  public render() {
    if (this.state.hasError) {
      return (
        <div className="min-h-[400px] flex items-center justify-center p-6">
          <div className="card max-w-lg w-full text-center space-y-6 animate-in fade-in zoom-in-95">
            <div className="inline-flex items-center justify-center w-16 h-16 rounded-full bg-red-500/10 text-red-500 mb-2">
              <AlertTriangle className="w-8 h-8" />
            </div>
            <div>
              <h2 className="text-xl font-semibold mb-2">Something went wrong</h2>
              <p className="text-slate-400">
                An unexpected error occurred in the application interface.
              </p>
            </div>
            
            {this.state.error && (
              <div className="text-left bg-slate-900 rounded-lg p-4 overflow-auto max-h-[150px] border border-slate-800">
                <code className="text-sm text-red-400 font-mono">
                  {this.state.error.toString()}
                </code>
              </div>
            )}
            
            <button 
              onClick={this.handleReset}
              className="btn btn-primary w-full inline-flex items-center justify-center gap-2"
            >
              <RefreshCcw className="w-4 h-4" />
              Reload Application
            </button>
          </div>
        </div>
      );
    }

    return this.props.children;
  }
}
