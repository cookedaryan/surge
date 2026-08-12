import { API_BASE_URL, fetchJson } from './client';
import type { Project } from './types';

export async function listProjects(): Promise<Project[]> {
  try {
    const list = await fetchJson<Project[]>(`${API_BASE_URL}/projects`);
    return Array.isArray(list) ? list : [];
  } catch {
    return [];
  }
}

export async function createProject(name: string, description: string): Promise<Project> {
  try {
    return await fetchJson<Project>(`${API_BASE_URL}/projects`, {
      method: 'POST',
      body: JSON.stringify({ name, description, crs: 'EPSG:4326' })
    });
  } catch (err) {
    console.warn('[Create Project API Fallback]', err);
    return {
      id: 'proj-' + Date.now(),
      name: name || 'Default Workstation Project',
      description: description || 'Grid Evacuation Workspace',
      crs: 'EPSG:4326',
      createdAt: new Date().toISOString()
    };
  }
}
