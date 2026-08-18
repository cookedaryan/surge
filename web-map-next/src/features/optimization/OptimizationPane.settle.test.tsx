import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { render } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import type { ReactNode } from 'react';
import { OptimizationPane } from './OptimizationPane';
import { useUiStore } from '../../lib/store';
import type { Job } from '../../lib/api';

/**
 * What happens when a run settles, and in what order.
 *
 * The map is keyed on `resultJobId`, so flipping it is what puts the new run on screen. Doing that
 * before the run's geometry is in the query cache made the map draw an empty result and only fill
 * in later — routes and poles appeared long after the success toast claimed they were ready. These
 * tests pin the ordering, not just the end state: an assertion that the cache is eventually
 * populated passes just as happily against the broken sequence.
 */

const PROJECT_ID = 'proj-1';
const JOB_ID = 'job-9';

const events: string[] = [];

let settle: ((job: Job) => void | Promise<void>) | null = null;

const routesFc = { type: 'FeatureCollection', features: [{ id: 'r1' }] };
const polesFc = { type: 'FeatureCollection', features: [{ id: 'p1' }] };

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

vi.mock('./useJobProgress', () => ({
  useJobProgress: (_p: string | null, _j: string | null, onSettled: (job: Job) => void) => {
    settle = onSettled;
    return null;
  }
}));

vi.mock('../../lib/query', () => ({
  useRunOptimization: () => ({ mutateAsync: vi.fn(), isPending: false }),
  useJob: () => ({ data: undefined })
}));

vi.mock('../../lib/api', () => ({
  api: {
    getRoutesGeoJson: vi.fn(async () => {
      events.push('routes-fetched');
      return routesFc;
    }),
    getPolesGeoJson: vi.fn(async () => {
      events.push('poles-fetched');
      return polesFc;
    })
  }
}));

let queryClient: QueryClient;
let unsubscribe: (() => void) | null = null;

function wrapper({ children }: { children: ReactNode }) {
  return <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>;
}

function completedJob(): Job {
  return { id: JOB_ID, status: 'COMPLETED' } as Job;
}

describe('OptimizationPane settle sequence', () => {
  beforeEach(() => {
    events.length = 0;
    settle = null;
    queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } });
    useUiStore.setState({
      currentProjectId: PROJECT_ID,
      currentJobId: JOB_ID,
      resultJobId: null,
      toasts: []
    });
    unsubscribe = useUiStore.subscribe((state, prev) => {
      if (state.resultJobId !== prev.resultJobId) events.push(`resultJobId=${state.resultJobId}`);
      // Toasts stack rather than replace, so a new one is a longer list — not a changed reference.
      if (state.toasts.length > prev.toasts.length) {
        events.push(`toast:${state.toasts[state.toasts.length - 1].variant}`);
      }
    });
  });

  // Subscriptions outlive the test that made them, so without this each later test records its
  // events once per test that ran before it.
  afterEach(() => unsubscribe?.());

  it('caches the finished run before pointing the map at it', async () => {
    render(<OptimizationPane />, { wrapper });
    await settle!(completedJob());

    // Both fetches must land before the map is switched over. If the switch came first the map
    // would mount an empty result and repaint only once its own request returned.
    expect(events).toEqual([
      'routes-fetched',
      'poles-fetched',
      `resultJobId=${JOB_ID}`,
      'toast:success'
    ]);
  });

  it('populates the exact query keys the map reads', async () => {
    render(<OptimizationPane />, { wrapper });
    await settle!(completedJob());

    // A near-miss key (a stale job id, a missing project id) would leave the map fetching from
    // scratch and reintroduce the blank interval, so assert the keys themselves.
    expect(queryClient.getQueryData(['routes', PROJECT_ID, JOB_ID])).toEqual(routesFc);
    expect(queryClient.getQueryData(['poles', PROJECT_ID, JOB_ID])).toEqual(polesFc);
  });

  it('does not advance the map when the run failed', async () => {
    render(<OptimizationPane />, { wrapper });
    await settle!({ id: JOB_ID, status: 'FAILED', errorMessage: 'no route found' } as Job);

    expect(useUiStore.getState().resultJobId).toBeNull();
    expect(events).toEqual(['toast:error']);
  });
});
