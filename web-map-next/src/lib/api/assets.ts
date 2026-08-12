import { API_BASE_URL, emptyGeoJson, fetchJson, uploadFile } from './client';
import type { CommitImportBody, CommitImportResult, FeatureCollection, ImportPreview } from './types';

export async function importGeoJsonAssets(projectId: string, geoJsonContent: unknown): Promise<unknown> {
  return await fetchJson(`${API_BASE_URL}/projects/${projectId}/assets/geojson`, {
    method: 'POST',
    body: typeof geoJsonContent === 'string' ? geoJsonContent : JSON.stringify(geoJsonContent)
  });
}

export async function importKmzAssets(projectId: string, fileBlob: File): Promise<unknown> {
  return await uploadFile(`${API_BASE_URL}/projects/${projectId}/assets/kmz`, fileBlob);
}

export async function previewKmzAssets(projectId: string, fileBlob: File): Promise<ImportPreview> {
  return await uploadFile<ImportPreview>(`${API_BASE_URL}/projects/${projectId}/assets/kmz/preview`, fileBlob);
}

export async function commitAssetImport(projectId: string, body: CommitImportBody): Promise<CommitImportResult> {
  return await fetchJson<CommitImportResult>(`${API_BASE_URL}/projects/${projectId}/assets/import/commit`, {
    method: 'POST',
    body: JSON.stringify(body)
  });
}

export async function getTowers(projectId: string): Promise<unknown> {
  return await fetchJson(`${API_BASE_URL}/projects/${projectId}/towers`);
}

export async function importParcelsGeoJson(projectId: string, geoJsonContent: unknown): Promise<unknown> {
  return await fetchJson(`${API_BASE_URL}/projects/${projectId}/parcels/geojson`, {
    method: 'POST',
    body: typeof geoJsonContent === 'string' ? geoJsonContent : JSON.stringify(geoJsonContent)
  });
}

export async function importRestrictedAreasGeoJson(projectId: string, geoJsonContent: unknown): Promise<unknown> {
  return await fetchJson(`${API_BASE_URL}/projects/${projectId}/restricted-areas/geojson`, {
    method: 'POST',
    body: typeof geoJsonContent === 'string' ? geoJsonContent : JSON.stringify(geoJsonContent)
  });
}

export async function getProjectAssetsGeoJson(projectId: string): Promise<FeatureCollection> {
  try {
    const res = await fetchJson<FeatureCollection>(`${API_BASE_URL}/projects/${projectId}/assets/geojson`);
    if (res && Array.isArray(res.features)) return res;
  } catch (e) {
    console.warn('[Assets API Error]', e);
  }
  return emptyGeoJson();
}

export async function getParcelsGeoJson(projectId: string): Promise<FeatureCollection> {
  try {
    const res = await fetchJson<FeatureCollection>(`${API_BASE_URL}/projects/${projectId}/parcels/geojson`);
    if (res && Array.isArray(res.features)) return res;
  } catch (e) {
    console.warn('[Parcels API Error]', e);
  }
  return emptyGeoJson();
}

export async function getRestrictedAreasGeoJson(projectId: string): Promise<FeatureCollection> {
  try {
    const res = await fetchJson<FeatureCollection>(`${API_BASE_URL}/projects/${projectId}/restricted-areas/geojson`);
    if (res && Array.isArray(res.features)) return res;
  } catch (e) {
    console.warn('[Restricted API Error]', e);
  }
  return emptyGeoJson();
}
