import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import type { ReactNode } from 'react';
import { OptimizationPane } from './OptimizationPane';
import { useUiStore } from '../../lib/store';

/**
 * The pane refuses to dispatch a job the backend would only reject, and says why. These are the
 * conditions that actually occur on real survey data — notably a project whose turbines are all
 * excluded by micro-siting status, which looks fully populated until you check.
 */

const counts = {
  wtgsTotal: 0,
  wtgsOptimisable: 0,
  substations: 0,
  towers: 0,
  referenceLines: 0,
  parcels: 0,
  restrictedAreas: 0
};

let mockData = { counts: { ...counts }, isLoading: false };

vi.mock('../map/useProjectData', () => ({
  useProjectData: () => ({
    ...mockData,
    wtgs: { type: 'FeatureCollection', features: [] },
    routes: { type: 'FeatureCollection', features: [] },
    bom: null
  })
}));

vi.mock('./useJobProgress', () => ({ useJobProgress: () => null }));

vi.mock('../../lib/query', () => ({
  useRunOptimization: () => ({ mutateAsync: vi.fn(), isPending: false }),
  // No job selected in these fixtures, so nothing is in flight and nothing has settled.
  useJob: () => ({ data: undefined })
}));

function wrapper({ children }: { children: ReactNode }) {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return <QueryClientProvider client={client}>{children}</QueryClientProvider>;
}

function runButton(): HTMLButtonElement {
  return screen.getByRole('button', { name: /run optimization/i }) as HTMLButtonElement;
}

describe('OptimizationPane run gating', () => {
  beforeEach(() => {
    mockData = { counts: { ...counts }, isLoading: false };
    useUiStore.setState({ currentProjectId: null, currentJobId: null });
  });

  it('blocks the run and says so when no project is selected', () => {
    render(<OptimizationPane />, { wrapper });

    expect(runButton()).toBeDisabled();
    expect(screen.getByText(/select a project first/i)).toBeInTheDocument();
  });

  it('blocks the run when the project has no turbines', () => {
    useUiStore.setState({ currentProjectId: 'p1' });
    render(<OptimizationPane />, { wrapper });

    expect(runButton()).toBeDisabled();
    expect(screen.getByText(/no wtgs imported/i)).toBeInTheDocument();
  });

  /**
   * The case worth guarding: 95 turbines imported and none usable. Without an explicit message the
   * operator sees a populated project and an unexplained failure.
   */
  it('explains when every imported turbine is excluded by status', () => {
    useUiStore.setState({ currentProjectId: 'p1' });
    mockData.counts = { ...counts, wtgsTotal: 95, wtgsOptimisable: 0, substations: 1 };
    render(<OptimizationPane />, { wrapper });

    expect(runButton()).toBeDisabled();
    expect(screen.getByText(/all 95 imported wtg\(s\) are excluded by status/i)).toBeInTheDocument();
  });

  it('blocks the run when no substation was imported', () => {
    useUiStore.setState({ currentProjectId: 'p1' });
    mockData.counts = { ...counts, wtgsTotal: 10, wtgsOptimisable: 10, substations: 0 };
    render(<OptimizationPane />, { wrapper });

    expect(runButton()).toBeDisabled();
    expect(screen.getByText(/no substation imported/i)).toBeInTheDocument();
  });

  it('allows the run once turbines and a substation are present', () => {
    useUiStore.setState({ currentProjectId: 'p1' });
    mockData.counts = { ...counts, wtgsTotal: 95, wtgsOptimisable: 38, substations: 1 };
    render(<OptimizationPane />, { wrapper });

    expect(runButton()).toBeEnabled();
  });

  /** Multiple substations are resolved automatically, so this informs rather than blocks. */
  it('notes automatic substation selection without blocking the run', () => {
    useUiStore.setState({ currentProjectId: 'p1' });
    mockData.counts = { ...counts, wtgsTotal: 95, wtgsOptimisable: 38, substations: 9 };
    render(<OptimizationPane />, { wrapper });

    expect(runButton()).toBeEnabled();
    expect(screen.getByText(/9 substations found/i)).toBeInTheDocument();
  });

  it('does not judge the project while its assets are still loading', () => {
    useUiStore.setState({ currentProjectId: 'p1' });
    mockData.isLoading = true;
    render(<OptimizationPane />, { wrapper });

    expect(runButton()).toBeDisabled();
    expect(screen.queryByText(/no wtgs imported/i)).not.toBeInTheDocument();
  });
});
