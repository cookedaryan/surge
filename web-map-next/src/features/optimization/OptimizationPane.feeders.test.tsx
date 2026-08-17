import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import type { ReactNode } from 'react';
import { OptimizationPane } from './OptimizationPane';
import { useUiStore } from '../../lib/store';

/**
 * Per-feeder electrical results, and the violations behind the network's violation count.
 *
 * Python computes both for every run. Java forwarded only the network totals, so a network reported
 * as valid could contain one feeder doing all the suffering, and "1 violation" told an operator that
 * something was wrong while giving them nowhere to look.
 *
 * The figures below are from a real run of the reference project: FDR-003 carries the highest losses
 * and sits at 1.055 pu, which is why the same project fails at the default 1.05 limit.
 */

const FEEDERS = [
  {
    feeder_id: 'FDR-001',
    active_loss_mw: 0.4125,
    maximum_loading_percent: 90.4,
    minimum_voltage_pu: 1.0,
    maximum_voltage_pu: 1.05,
    valid: true
  },
  {
    feeder_id: 'FDR-003',
    active_loss_mw: 0.5176,
    maximum_loading_percent: 91.3,
    minimum_voltage_pu: 1.0,
    maximum_voltage_pu: 1.055,
    valid: false
  }
];

const VIOLATIONS = [
  {
    code: 'BUS_OVERVOLTAGE',
    message: 'bus above limit',
    scope: 'node',
    node_id: 'wtg:KS-51_S3',
    measured_value: 1.06,
    limit_value: 1.05
  }
];

function summaryJson(extra: Record<string, unknown>): string {
  return JSON.stringify({
    workflowStatus: 'SUCCESS',
    recommendation: { reasons: ['lowest lifecycle cost'] },
    ...extra
  });
}

let jobData: unknown = undefined;

vi.mock('../map/useProjectData', () => ({
  useProjectData: () => ({
    counts: {
      wtgsTotal: 3,
      wtgsOptimisable: 3,
      substations: 1,
      towers: 0,
      referenceLines: 0,
      parcels: 0,
      restrictedAreas: 0
    },
    isLoading: false,
    wtgs: { type: 'FeatureCollection', features: [] },
    routes: { type: 'FeatureCollection', features: [] },
    bom: null
  })
}));

vi.mock('./useJobProgress', () => ({ useJobProgress: () => null }));

vi.mock('../../lib/query', () => ({
  useRunOptimization: () => ({ mutateAsync: vi.fn(), isPending: false }),
  useJob: () => ({ data: jobData })
}));

function wrapper({ children }: { children: ReactNode }) {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return <QueryClientProvider client={client}>{children}</QueryClientProvider>;
}

describe('per-feeder electrical breakdown', () => {
  beforeEach(() => {
    useUiStore.setState({ currentProjectId: 'p1', currentJobId: 'j1' });
    jobData = {
      id: 'j1',
      status: 'COMPLETED',
      scenario: 'Balanced',
      resultSummaryJson: summaryJson({ feeders: FEEDERS })
    };
  });

  it('is collapsed by default, because on a normal run it is detail', async () => {
    render(<OptimizationPane />, { wrapper });

    expect(screen.getByRole('button', { name: /per-feeder electrical/i })).toHaveProperty(
      'ariaExpanded',
      'false'
    );
    expect(screen.queryByText('FDR-003')).toBeNull();
  });

  it('names every feeder with its losses, loading and voltage range when expanded', async () => {
    render(<OptimizationPane />, { wrapper });
    await userEvent.click(screen.getByRole('button', { name: /per-feeder electrical/i }));

    expect(screen.getByText('FDR-001')).toBeTruthy();
    expect(screen.getByText('FDR-003')).toBeTruthy();
    // Losses arrive in MW and are shown in kW, matching every other loss figure in the UI.
    expect(screen.getByText('517.6 kW')).toBeTruthy();
    expect(screen.getByText('91.3%')).toBeTruthy();
    expect(screen.getByText('1.055')).toBeTruthy();
  });

  it('says how many feeders are invalid without needing to be opened', () => {
    // The point of the collapsed header: an operator should not have to expand a section to learn
    // that something in it is wrong.
    render(<OptimizationPane />, { wrapper });

    expect(screen.getByRole('button', { name: /1 invalid/i })).toBeTruthy();
  });

  it('shows nothing at all when the run reported no feeders', () => {
    jobData = {
      id: 'j1',
      status: 'COMPLETED',
      scenario: 'Balanced',
      resultSummaryJson: summaryJson({})
    };
    render(<OptimizationPane />, { wrapper });

    expect(screen.queryByRole('button', { name: /per-feeder electrical/i })).toBeNull();
  });
});

describe('violation details', () => {
  beforeEach(() => {
    useUiStore.setState({ currentProjectId: 'p1', currentJobId: 'j1' });
    jobData = {
      id: 'j1',
      status: 'COMPLETED',
      scenario: 'Balanced',
      resultSummaryJson: summaryJson({ violations: VIOLATIONS })
    };
  });

  it('names where the limit was breached and by how much', () => {
    render(<OptimizationPane />, { wrapper });

    // "1 violation" is not actionable. The bus, the measured value and the limit are.
    expect(screen.getByText(/bus overvoltage/i)).toBeTruthy();
    expect(screen.getByText(/wtg:KS-51_S3/)).toBeTruthy();
    expect(screen.getByText(/1\.06 vs 1\.05 limit/)).toBeTruthy();
  });

  it('shows no violation section on a clean run', () => {
    jobData = {
      id: 'j1',
      status: 'COMPLETED',
      scenario: 'Balanced',
      resultSummaryJson: summaryJson({ violations: [] })
    };
    render(<OptimizationPane />, { wrapper });

    expect(screen.queryByText(/^Violations/i)).toBeNull();
  });
});
