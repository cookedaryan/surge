import { API_BASE_URL, fetchJson } from './client';
import type { Project } from './types';

/**
 * Lists the caller's projects.
 *
 * Failures propagate deliberately. Swallowing them into an empty array makes a rejected session
 * indistinguishable from a genuinely empty account, which previously caused the UI to "helpfully"
 * create a replacement project on top of data it simply was not allowed to read yet.
 */
export async function listProjects(): Promise<Project[]> {
  const list = await fetchJson<Project[]>(`${API_BASE_URL}/projects`);
  return Array.isArray(list) ? list : [];
}

/**
 * Creates a project.
 *
 * A failure here is reported, never faked. Returning a fabricated project with a client-generated
 * id used to leave the operator working against something the backend had never stored — every
 * subsequent import and optimisation would fail against an id that does not exist.
 */
export async function createProject(name: string, description: string): Promise<Project> {
  return await fetchJson<Project>(`${API_BASE_URL}/projects`, {
    method: 'POST',
    body: JSON.stringify({ name, description, crs: 'EPSG:4326' })
  });
}
