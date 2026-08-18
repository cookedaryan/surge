import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { getRoutesGeoJson, getPolesGeoJson } from './jobs';
import { setToken } from './client';

const PROJECT = '11111111-1111-1111-1111-111111111111';
const JOB = '22222222-2222-2222-2222-222222222222';

/**
 * These fetchers used to catch every failure and return an empty feature collection, so a failed
 * request looked exactly like a network with no routes: the map went blank, nothing was reported,
 * and the empty answer was cached as though it were true. A transaction-visibility bug hid behind
 * that for an hour, reading as "the optimiser produced nothing".
 */

const routes = {
  type: 'FeatureCollection',
  features: [{ type: 'Feature', geometry: null, properties: { feederName: 'FDR-001' } }]
};

describe('route and pole GeoJSON fetching', () => {
  beforeEach(() => {
    setToken('test-token');
  });

  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it('returns the collection the server sent', async () => {
    vi.stubGlobal('fetch', vi.fn(async () => new Response(JSON.stringify(routes), { status: 200, headers: { 'content-type': 'application/json' } })));

    await expect(getRoutesGeoJson(PROJECT, JOB)).resolves.toEqual(routes);
  });

  it('reports an empty result as empty, not as a failure', async () => {
    const empty = { type: 'FeatureCollection', features: [] };
    vi.stubGlobal('fetch', vi.fn(async () => new Response(JSON.stringify(empty), { status: 200, headers: { 'content-type': 'application/json' } })));

    // A run that genuinely produced nothing is a legitimate answer and must still resolve.
    await expect(getRoutesGeoJson(PROJECT, JOB)).resolves.toEqual(empty);
  });

  it('throws when the request fails rather than reporting no routes', async () => {
    vi.stubGlobal('fetch', vi.fn(async () => new Response('upstream exploded', { status: 500 })));

    await expect(getRoutesGeoJson(PROJECT, JOB)).rejects.toThrow();
  });

  it('throws when the network is unreachable', async () => {
    vi.stubGlobal('fetch', vi.fn(async () => {
      throw new TypeError('Failed to fetch');
    }));

    await expect(getPolesGeoJson(PROJECT, JOB)).rejects.toThrow();
  });

  it('throws when the body is not a feature collection', async () => {
    // A 200 carrying the wrong shape is still a failure; treating it as "no features" would draw
    // an empty map and call it success.
    vi.stubGlobal('fetch', vi.fn(async () => new Response(JSON.stringify({ nope: true }), { status: 200, headers: { 'content-type': 'application/json' } })));

    await expect(getRoutesGeoJson(PROJECT, JOB)).rejects.toThrow(/unreadable/i);
  });

  it('falls back to the latest run when given no job id', async () => {
    const fetchMock = vi.fn(async (url: RequestInfo | URL) => {
      void url;
      return new Response(JSON.stringify(routes), { status: 200, headers: { 'content-type': 'application/json' } });
    });
    vi.stubGlobal('fetch', fetchMock);

    await getRoutesGeoJson(PROJECT, null);

    expect(String(fetchMock.mock.calls[0][0])).toContain('/routes/latest/geojson');
  });

  // A project that has never been optimised has no latest run. The API reports that with a 400
  // naming the condition, and treating it as a load failure put a red "the map is not showing
  // everything" banner over every newly created project.
  const noRuns = () =>
    new Response(
      JSON.stringify({ status: 400, message: 'No completed optimization jobs found for project: ' + PROJECT }),
      { status: 400, headers: { 'content-type': 'application/json' } }
    );

  it('reports a project with no completed runs as empty rather than broken', async () => {
    vi.stubGlobal('fetch', vi.fn(async () => noRuns()));

    await expect(getRoutesGeoJson(PROJECT, null)).resolves.toEqual({ type: 'FeatureCollection', features: [] });
    await expect(getPolesGeoJson(PROJECT, null)).resolves.toEqual({ type: 'FeatureCollection', features: [] });
  });

  it('still throws for a named job, which cannot be missing for want of any run', async () => {
    vi.stubGlobal('fetch', vi.fn(async () => noRuns()));

    await expect(getRoutesGeoJson(PROJECT, JOB)).rejects.toThrow();
  });

  it('still throws on other latest-run failures', async () => {
    // The allowance is for one specific condition, not for 4xx and 5xx generally.
    vi.stubGlobal('fetch', vi.fn(async () => new Response('upstream exploded', { status: 500 })));

    await expect(getRoutesGeoJson(PROJECT, null)).rejects.toThrow();
  });
});
