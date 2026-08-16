import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { render, screen } from '@testing-library/react';
import { ErrorBoundary } from './ErrorBoundary';

/**
 * Without a boundary, any exception thrown during render unmounts the whole tree and leaves a
 * blank white page — no message, no way back, nothing for the operator to report.
 */

function Explodes(): JSX.Element {
  throw new Error('feeder renderer blew up');
}

describe('ErrorBoundary', () => {
  beforeEach(() => {
    // React logs caught errors to the console by design; silenced so the run stays readable.
    vi.spyOn(console, 'error').mockImplementation(() => {});
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  it('renders children when nothing goes wrong', () => {
    render(
      <ErrorBoundary>
        <p>workstation</p>
      </ErrorBoundary>
    );

    expect(screen.getByText('workstation')).toBeTruthy();
  });

  it('shows an explanation instead of a blank page when a child throws', () => {
    render(
      <ErrorBoundary>
        <Explodes />
      </ErrorBoundary>
    );

    expect(screen.getByRole('alert')).toBeTruthy();
    expect(screen.getByText(/something broke on screen/i)).toBeTruthy();
  });

  it('surfaces the underlying message so the failure can be reported', () => {
    render(
      <ErrorBoundary>
        <Explodes />
      </ErrorBoundary>
    );

    expect(screen.getByText(/feeder renderer blew up/)).toBeTruthy();
  });

  it('offers a way back', () => {
    render(
      <ErrorBoundary>
        <Explodes />
      </ErrorBoundary>
    );

    expect(screen.getByRole('button', { name: /reload/i })).toBeTruthy();
  });

  it('reassures that server-side work is unaffected', () => {
    // The operator's first question after a crash mid-run is whether they lost the run.
    render(
      <ErrorBoundary>
        <Explodes />
      </ErrorBoundary>
    );

    expect(screen.getByText(/continues on the server/i)).toBeTruthy();
  });
});
