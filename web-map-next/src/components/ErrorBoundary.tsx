import { Component } from 'react';
import type { ErrorInfo, ReactNode } from 'react';

interface Props {
  children: ReactNode;
}

interface State {
  error: Error | null;
}

/**
 * Catches render errors so one broken component does not take the whole workstation with it.
 *
 * <p>Without this, any exception thrown during render unmounts the entire tree and leaves a blank
 * white page — no message, no way back, and nothing to report beyond "it disappeared". React
 * offers no other mechanism: a boundary has to be a class component.
 *
 * <p>Recovery is a reload rather than a state reset. The tree that threw is not trustworthy, and
 * work in progress lives on the server, so a clean reload is both safer and honest about what it
 * does.
 */
export class ErrorBoundary extends Component<Props, State> {
  state: State = { error: null };

  static getDerivedStateFromError(error: Error): State {
    return { error };
  }

  componentDidCatch(error: Error, info: ErrorInfo): void {
    // Kept in the console so the component stack survives for whoever investigates; the operator
    // gets the readable version below.
    console.error('Unhandled render error:', error, info.componentStack);
  }

  render(): ReactNode {
    const { error } = this.state;
    if (!error) {
      return this.props.children;
    }

    return (
      <div
        role="alert"
        className="fixed inset-0 z-[30000] flex items-center justify-center bg-black/85 p-6 font-ui"
      >
        <div className="w-[440px] rounded-lg border border-danger bg-panel p-5">
          <h2 className="m-0 mb-2 text-[13.5px] font-bold text-danger">Something broke on screen</h2>
          <p className="m-0 mb-3 text-[11.5px] text-textFaint">
            Part of the interface failed to render. Nothing you have saved is affected, and any
            optimisation already running continues on the server.
          </p>
          <pre className="m-0 mb-3 max-h-32 overflow-auto rounded-md border border-borderStrong bg-surface2 p-2.5 text-[11px] text-text">
            {error.message || String(error)}
          </pre>
          <button
            onClick={() => window.location.reload()}
            className="h-8 w-full rounded-md border border-borderStrong bg-surface2 text-[11.5px] text-text hover:border-accent"
          >
            Reload the workstation
          </button>
        </div>
      </div>
    );
  }
}
