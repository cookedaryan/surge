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

export async function register(username: string, email: string, password: string): Promise<AuthResponse> {
  const res = await fetchJson<AuthResponse>(`${API_BASE_URL}/auth/register`, {
    method: 'POST',
    body: JSON.stringify({ username, email, password, role: 'ROLE_ENGINEER' })
  });
  if (res.token) setToken(res.token);
  return res;
}
