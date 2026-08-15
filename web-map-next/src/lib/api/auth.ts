import { API_BASE_URL, fetchJson, setToken } from './client';
import type { AuthResponse } from './types';

export async function login(username: string, password: string): Promise<AuthResponse> {
  const res = await fetchJson<AuthResponse>(`${API_BASE_URL}/auth/login`, {
    method: 'POST',
    body: JSON.stringify({ username, password })
  });
  if (res.token) setToken(res.token);
  return res;
}

/**
 * Resolves the signed-in account from the stored token.
 *
 * Used to restore a session across a page reload. Asking the server is deliberate: it revalidates
 * the token at the same time, so an expired one drops the operator back to the sign-in screen
 * instead of leaving them in an app that appears usable but rejects every request. The role must
 * also come from the server rather than local storage, since it decides what the UI offers.
 */
export async function getCurrentUser(): Promise<AuthResponse> {
  return await fetchJson<AuthResponse>(`${API_BASE_URL}/auth/me`);
}

export async function register(username: string, email: string, password: string): Promise<AuthResponse> {
  const res = await fetchJson<AuthResponse>(`${API_BASE_URL}/auth/register`, {
    method: 'POST',
    body: JSON.stringify({ username, email, password, role: 'ROLE_ENGINEER' })
  });
  if (res.token) setToken(res.token);
  return res;
}
