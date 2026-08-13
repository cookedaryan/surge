import { API_BASE_URL, emptyGeoJson, fetchJson } from './client';
import type { FeatureCollection, Job, JobProgress, OptimizationParams } from './types';

export async function getRoutesGeoJson(projectId: string, jobId?: string | null): Promise<FeatureCollection> {
  // Without a specific jobId (e.g. on page load, or after switching to a project that
  // already has a completed run from an earlier session) fall back to the project's most
  // recent completed job instead of rendering an empty map.
  const url = jobId
    ? `${API_BASE_URL}/projects/${projectId}/jobs/${jobId}/routes/geojson`
    : `${API_BASE_URL}/projects/${projectId}/routes/latest/geojson`;
  try {
    const res = await fetchJson<FeatureCollection>(url);
    if (res && Array.isArray(res.features)) return res;
  } catch (e) {
    console.warn('[Routes API Error]', e);
  }
  return emptyGeoJson();
}

export async function getPolesGeoJson(projectId: string, jobId?: string | null): Promise<FeatureCollection> {
  const url = jobId
    ? `${API_BASE_URL}/projects/${projectId}/jobs/${jobId}/poles/geojson`
    : `${API_BASE_URL}/projects/${projectId}/poles/latest/geojson`;
  try {
    const res = await fetchJson<FeatureCollection>(url);
    if (res && Array.isArray(res.features)) return res;
  } catch (e) {
    console.warn('[Poles API Error]', e);
  }
  return emptyGeoJson();
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

export function listenJobProgress(
  projectId: string,
  jobId: string,
  onProgress?: (data: JobProgress) => void,
  onError?: (err: Error) => void,
  onComplete?: (data: JobProgress) => void
): () => void {
  const url = `${API_BASE_URL}/projects/${projectId}/jobs/${jobId}/progress`;
  let eventSource: EventSource;
  try {
    eventSource = new EventSource(url);

    eventSource.addEventListener('progress', (e: MessageEvent) => {
      try {
        const data: JobProgress = JSON.parse(e.data);
        if (onProgress) onProgress(data);
        if (data.status === 'COMPLETED' || data.status === 'FAILED') {
          eventSource.close();
          if (data.status === 'COMPLETED' && onComplete) onComplete(data);
          if (data.status === 'FAILED' && onError) onError(new Error(data.message || 'Job failed'));
        }
      } catch (err) {
        console.warn('[SSE Parse Error]', err);
      }
    });

    eventSource.onerror = (err) => {
      eventSource.close();
      if (onError) onError(err as unknown as Error);
    };

    return () => eventSource.close();
  } catch (err) {
    if (onError) onError(err as Error);
    return () => {};
  }
}
