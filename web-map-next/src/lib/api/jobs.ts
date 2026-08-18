import { API_BASE_URL, fetchJson, getToken, notifyUnauthorized } from './client';
import type { FeatureCollection, Job, JobProgress, OptimizationParams } from './types';

export async function getRoutesGeoJson(projectId: string, jobId?: string | null): Promise<FeatureCollection> {
  // Without a specific jobId (e.g. on page load, or after switching to a project that
  // already has a completed run from an earlier session) fall back to the project's most
  // recent completed job instead of rendering an empty map.
  if (!jobId) {
    return fetchLatestGeoJson(`${API_BASE_URL}/projects/${projectId}/routes/latest/geojson`, 'routes');
  }
  return fetchGeoJsonOrThrow(`${API_BASE_URL}/projects/${projectId}/jobs/${jobId}/routes/geojson`, 'routes');
}

export async function getPolesGeoJson(projectId: string, jobId?: string | null): Promise<FeatureCollection> {
  if (!jobId) {
    return fetchLatestGeoJson(`${API_BASE_URL}/projects/${projectId}/poles/latest/geojson`, 'poles');
  }
  return fetchGeoJsonOrThrow(`${API_BASE_URL}/projects/${projectId}/jobs/${jobId}/poles/geojson`, 'poles');
}

/**
 * The "most recent run" endpoints, where having never run is a normal state rather than a failure.
 *
 * <p>A project that has not been optimised yet has no latest job, and the API says so with a 400
 * naming that exact condition. Treated as an error — which it was — every newly created project
 * opened under a red banner reading "the map is not showing everything, reload before relying on
 * it", about a map that was showing everything there was.
 *
 * <p>Narrow on purpose. Only this endpoint, and only this one condition, resolves to an empty
 * collection; every other failure still throws, because the reason these fetchers stopped
 * swallowing errors in the first place was a real fault that spent an hour disguised as
 * "the optimiser produced nothing" (see {@link fetchGeoJsonOrThrow}).
 */
async function fetchLatestGeoJson(url: string, what: string): Promise<FeatureCollection> {
  try {
    return await fetchGeoJsonOrThrow(url, what);
  } catch (err) {
    if (/no completed optimization jobs/i.test((err as Error).message)) {
      return { type: 'FeatureCollection', features: [] };
    }
    throw err;
  }
}

/**
 * Fetches a feature collection, failing loudly when it cannot.
 *
 * <p>These used to catch every error and return an empty collection, which made a failed request
 * indistinguishable from a network that genuinely has no routes: the map went blank, no error was
 * shown, and the empty answer was cached as though it were the truth. That is how a
 * transaction-visibility bug spent an hour looking like "the optimiser produced nothing".
 *
 * <p>Throwing instead lets the query layer mark the fetch as failed, so the panels can say so and
 * a retry becomes possible. An empty collection is now only ever a real, empty answer.
 */
async function fetchGeoJsonOrThrow(url: string, what: string): Promise<FeatureCollection> {
  const res = await fetchJson<FeatureCollection>(url);
  if (!res || !Array.isArray(res.features)) {
    throw new Error(`The server returned an unreadable ${what} response.`);
  }
  return res;
}

export async function runOptimization(projectId: string, params: Partial<OptimizationParams> = {}): Promise<Job> {
  return await fetchJson<Job>(`${API_BASE_URL}/projects/${projectId}/jobs`, {
    method: 'POST',
    body: JSON.stringify({
      algorithmType: 'MULTI_OBJECTIVE_A_STAR',
      scenario: params.scenario || 'Balanced',
      feederCapacityMw: params.feederCapacityMw || 20.0,
      maxSpanMeters: params.maxSpanMeters || 150.0,
      voltageKv: params.voltageKv || 33.0
    })
  });
}

export async function getJobStatus(projectId: string, jobId: string): Promise<Job> {
  return await fetchJson<Job>(`${API_BASE_URL}/projects/${projectId}/jobs/${jobId}`);
}

/**
 * Streams job progress over fetch rather than EventSource.
 *
 * EventSource cannot attach an Authorization header, and the progress endpoint requires a token
 * like every other project route. Passing the JWT as a query parameter would "work" but leaks the
 * credential into access logs, browser history and referrer headers, so the stream is read
 * manually instead. Returns an unsubscribe function that aborts the in-flight request.
 */
export function listenJobProgress(
  projectId: string,
  jobId: string,
  onProgress?: (data: JobProgress) => void,
  onError?: (err: Error) => void,
  onComplete?: (data: JobProgress) => void
): () => void {
  const url = `${API_BASE_URL}/projects/${projectId}/jobs/${jobId}/progress`;
  const controller = new AbortController();
  let finished = false;

  const finish = (fn?: () => void) => {
    if (finished) return;
    finished = true;
    controller.abort();
    fn?.();
  };

  const handleFrame = (frame: string) => {
    // Unsubscribing must stop delivery immediately. Aborting the request is not sufficient on its
    // own: bytes already buffered would still be parsed and dispatched before the loop next checks
    // its exit condition, so a caller that has torn down would keep receiving callbacks.
    if (finished) return;

    // An SSE frame is a block of "field: value" lines. Only the data payload matters here; the
    // event name is always "progress" and reconnection hints are unused for a short-lived job.
    const data = frame
      .split('\n')
      .filter((line) => line.startsWith('data:'))
      .map((line) => line.slice(5).trim())
      .join('\n');
    if (!data) return;

    let parsed: JobProgress;
    try {
      parsed = JSON.parse(data);
    } catch (err) {
      console.warn('[SSE Parse Error]', err);
      return;
    }

    onProgress?.(parsed);
    if (parsed.status === 'COMPLETED') finish(() => onComplete?.(parsed));
    if (parsed.status === 'FAILED') finish(() => onError?.(new Error(parsed.message || 'Job failed')));
  };

  (async () => {
    try {
      const token = getToken();
      const res = await fetch(url, {
        headers: {
          Accept: 'text/event-stream',
          ...(token ? { Authorization: `Bearer ${token}` } : {})
        },
        signal: controller.signal
      });

      if (res.status === 401) {
        notifyUnauthorized();
        throw new Error('Session expired while streaming job progress.');
      }
      if (!res.ok || !res.body) {
        throw new Error(`Progress stream failed: ${res.status} ${res.statusText}`);
      }

      const reader = res.body.getReader();
      const decoder = new TextDecoder();
      let buffer = '';

      for (;;) {
        const { done, value } = await reader.read();
        if (done) break;

        // Chunks can split a frame anywhere, so hold the remainder until its blank-line terminator.
        buffer += decoder.decode(value, { stream: true });
        const frames = buffer.split(/\r?\n\r?\n/);
        buffer = frames.pop() ?? '';
        frames.forEach(handleFrame);
        if (finished) return;
      }

      if (buffer.trim()) handleFrame(buffer);
      // The server closing the stream without a terminal status is not an error on its own: the
      // caller polls the job record separately and will pick up the final state from there.
      finish();
    } catch (err) {
      if ((err as Error).name === 'AbortError') return;
      finish(() => onError?.(err as Error));
    }
  })();

  return () => finish();
}
