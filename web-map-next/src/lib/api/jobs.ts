import { API_BASE_URL, emptyGeoJson, fetchJson } from './client';
import type { FeatureCollection, Job, JobProgress, OptimizationParams } from './types';

export async function getRoutesGeoJson(projectId: string, jobId?: string | null): Promise<FeatureCollection> {
  try {
    if (jobId) {
      const res = await fetchJson<FeatureCollection>(
        `${API_BASE_URL}/projects/${projectId}/jobs/${jobId}/routes/geojson`
      );
      if (res && Array.isArray(res.features)) return res;
    }
  } catch (e) {
    console.warn('[Routes API Error]', e);
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
