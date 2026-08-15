const API_BASE_URL = '/api/v1';
const TOKEN_KEY = 'surge_jwt_token';

export function getToken(): string | null {
  return localStorage.getItem(TOKEN_KEY);
}

export function setToken(token: string): void {
  localStorage.setItem(TOKEN_KEY, token);
}

let unauthorizedHandler: (() => void) | null = null;

/**
 * Registers what to do when the API rejects our credentials.
 *
 * Sign-in state is inferred from a token merely being present in storage, so an expired token
 * would otherwise leave the app looking signed in while every request fails with an opaque error
 * and no route back to the login screen.
 */
export function setUnauthorizedHandler(handler: () => void): void {
  unauthorizedHandler = handler;
}

/** Drops the rejected token and notifies the app. Safe to call from any transport. */
export function notifyUnauthorized(): void {
  localStorage.removeItem(TOKEN_KEY);
  unauthorizedHandler?.();
}

export async function fetchJson<T>(url: string, options: RequestInit = {}): Promise<T> {
  const token = getToken();
  const headers: Record<string, string> = {
    'Content-Type': 'application/json',
    ...(options.headers as Record<string, string> | undefined)
  };
  if (token) headers['Authorization'] = `Bearer ${token}`;

  const response = await fetch(url, { ...options, headers });
  if (!response.ok) {
    if (response.status === 401) notifyUnauthorized();
    const errorText = await response.text();
    throw new Error(errorText || `HTTP Error ${response.status}`);
  }

  const contentType = response.headers.get('content-type');
  if (contentType && contentType.includes('application/json')) {
    return (await response.json()) as T;
  }
  return (await response.text()) as unknown as T;
}

export async function uploadFile<T>(url: string, fileBlob: File | Blob): Promise<T> {
  const formData = new FormData();
  formData.append('file', fileBlob);
  const token = getToken();
  const headers: Record<string, string> = token ? { Authorization: `Bearer ${token}` } : {};

  const response = await fetch(url, { method: 'POST', headers, body: formData });
  if (!response.ok) {
    if (response.status === 401) notifyUnauthorized();
    const errorText = await response.text();
    throw new Error(errorText || `HTTP Error ${response.status}`);
  }
  return (await response.json()) as T;
}

export function emptyGeoJson(): import('./types').FeatureCollection {
  return { type: 'FeatureCollection', features: [] };
}

export { API_BASE_URL };
