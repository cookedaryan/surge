import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import type { ReactNode } from 'react';
import { OptimizationPane } from './OptimizationPane';
import { useUiStore } from '../../lib/store';

/**
 * The diagnostics behind a failed run.
 *
 * Payload below is copied from a real failure of the reference project at the default 1.05 pu limit:
 * six buses over voltage, no conductor upgrades attempted, and Quad Panther as the catalogue ceiling.
 * The full-precision measured values are deliberate — they are what the engine actually sends.
 */

const DETAILS = {
  status: 'REPAIR_EXHAUSTED',
  summary:
    'Electrical repair exhausted: BUS_OVERVOLTAGE at wtg:KS-51_S3; measured 1.06 against a limit of 1.05; the largest conductor available was ACSR-QUAD-PANTHER at 1880 A effective.',
  unresolved_violations: [
    {
      code: 'BUS_OVERVOLTAGE',
      message: "Bus 'wtg:KS-51_S3' voltage 1.0600 is above maximum 1.05",
      segment_id: null,
      node_id: 'wtg:KS-51_S3',
      feeder_id: null,
      measured_value: 1.0599745548368775,
      limit_value: 1.05
    },
    {
      code: 'BUS_OVERVOLTAGE',
      message: "Bus 'wtg:KS49_S2' voltage 1.0631 is above maximum 1.05",
      segment_id: null,
      node_id: 'wtg:KS49_S2',
      feeder_id: null,
      measured_value: 1.063088856059541,
      limit_value: 1.05
    }
  ],
  repair_attempts: [],
  largest_cable_available: {
    cable_type_id: 'ACSR-QUAD-PANTHER',
    effective_ampacity_a: 1880.0,
    parallel_count: 4
  },
  catalogue_size: 8
};

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

function failedJob(summary: Record<string, unknown>) {
  return {
    id: 'j1',
    status: 'FAILED',
    scenario: 'Balanced',
    errorMessage: `Optimization failed: ${DETAILS.summary}`,
    resultSummaryJson: JSON.stringify({ workflowStatus: 'NO_FEASIBLE_CANDIDATE', ...summary })
  };
}

describe('repair diagnostics on a failed run', () => {
  beforeEach(() => {
    useUiStore.setState({ currentProjectId: 'p1', currentJobId: 'j1' });
    jobData = failedJob({
      candidates: [
        {
          scenario_id: 'SCN-001',
          strategy: 'baseline',
          electrical_status: 'INVALID',
          execution_failure: {
            code: 'ELECTRICAL_VALIDATION_FAILED',
            message: DETAILS.summary,
            details: DETAILS
          }
        }
      ],
      failures: [
        {
          stage: 'ELECTRICAL_VALIDATION',
          code: 'ELECTRICAL_VALIDATION_FAILED',
          message: DETAILS.summary
        }
      ]
    });
  });

  it('names each bus that stayed over its limit', () => {
    render(<OptimizationPane />, { wrapper });

    expect(screen.getByText('Unresolved (2)')).toBeTruthy();
    expect(screen.getByText('wtg:KS-51_S3')).toBeTruthy();
    expect(screen.getByText('wtg:KS49_S2')).toBeTruthy();
  });

  it('rounds measured values instead of printing float noise', () => {
    render(<OptimizationPane />, { wrapper });

    // 1.0599745548368775 is unreadable and 1.06 is the number the engine's own message quotes.
    expect(screen.getByText('1.06 / 1.05 limit')).toBeTruthy();
    expect(screen.getByText('1.0631 / 1.05 limit')).toBeTruthy();
    expect(screen.queryByText(/1\.0599745/)).toBeNull();
  });

  it('says no upgrades were attempted rather than showing an empty list', () => {
    // Repair only upgrades conductors to clear overloads, so zero attempts on a voltage failure is
    // the finding: a bigger conductor was never the lever.
    render(<OptimizationPane />, { wrapper });

    expect(screen.getByText('Conductor upgrades (0)')).toBeTruthy();
    expect(screen.getByText('None attempted.')).toBeTruthy();
  });

  it('reports the catalogue ceiling repair was working against', () => {
    render(<OptimizationPane />, { wrapper });

    const line = screen.getByText(/Largest of 8 conductors/).closest('p');
    expect(line?.textContent).toContain('ACSR-QUAD-PANTHER');
    expect(line?.textContent).toContain('at 1880 A');
    expect(line?.textContent).toContain('(4×)');
  });

  it('does not repeat a failure already shown against its candidate', () => {
    // Every electrically-failed candidate produces both an execution_failure and a failures entry
    // carrying the same sentence. With three candidates the card printed each one twice.
    render(<OptimizationPane />, { wrapper });

    expect(screen.queryByText(/ELECTRICAL_VALIDATION/)).toBeNull();
  });

  it('still shows failures that belong to no candidate', () => {
    jobData = failedJob({
      candidates: [],
      failures: [{ stage: 'GENERATION', code: 'NO_CANDIDATES', message: 'No topology could be built' }]
    });
    render(<OptimizationPane />, { wrapper });

    expect(screen.getByText(/No topology could be built/)).toBeTruthy();
  });

  it('lists the upgrades and the loading they moved when repair did try', () => {
    jobData = failedJob({
      candidates: [
        {
          scenario_id: 'SCN-001',
          strategy: 'baseline',
          electrical_status: 'INVALID',
          execution_failure: {
            code: 'ELECTRICAL_VALIDATION_FAILED',
            message: 'overload remained',
            details: {
              ...DETAILS,
              repair_attempts: [
                {
                  segment_id: 'SEG-14',
                  iteration: 1,
                  from_cable_type_id: 'ACSR-PANTHER',
                  to_cable_type_id: 'ACSR-QUAD-PANTHER',
                  reason_code: 'OVERLOAD_CAPACITY_UPGRADE',
                  pre_repair_loading_pct: 142.35019,
                  post_repair_loading_pct: 71.1751
                }
              ]
            }
          }
        }
      ],
      failures: []
    });
    render(<OptimizationPane />, { wrapper });

    expect(screen.getByText('Conductor upgrades (1)')).toBeTruthy();
    expect(screen.getByText('SEG-14')).toBeTruthy();
    expect(screen.getByText(/ACSR-PANTHER → ACSR-QUAD-PANTHER/)).toBeTruthy();
    expect(screen.getByText(/142\.3502% → 71\.1751%/)).toBeTruthy();
  });

  it('shows the failure card unchanged when a run carries no diagnostics', () => {
    jobData = failedJob({
      candidates: [{ scenario_id: 'SCN-001', strategy: 'baseline' }],
      failures: [{ stage: 'ROUTING', code: 'NO_PATH', message: 'No feasible path' }]
    });
    render(<OptimizationPane />, { wrapper });

    expect(screen.getByText('SCN-001')).toBeTruthy();
    expect(screen.getByText(/No feasible path/)).toBeTruthy();
    expect(screen.queryByText(/Conductor upgrades/)).toBeNull();
  });
});
