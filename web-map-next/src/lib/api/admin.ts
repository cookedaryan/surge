import { API_BASE_URL, fetchJson } from './client';
import type { AdminUser, UserRole } from './types';

export async function listUsers(): Promise<AdminUser[]> {
  const list = await fetchJson<AdminUser[]>(`${API_BASE_URL}/admin/users`);
  return Array.isArray(list) ? list : [];
}

export async function createUser(input: {
  username: string;
  email: string;
  password: string;
  role: UserRole;
}): Promise<AdminUser> {
  return await fetchJson<AdminUser>(`${API_BASE_URL}/admin/users`, {
    method: 'POST',
    body: JSON.stringify(input)
  });
}

/** Partial update: omit a field to leave it unchanged. */
export async function updateUser(
  userId: string,
  changes: { role?: UserRole; enabled?: boolean }
): Promise<AdminUser> {
  return await fetchJson<AdminUser>(`${API_BASE_URL}/admin/users/${userId}`, {
    method: 'PATCH',
    body: JSON.stringify(changes)
  });
}

export async function resetUserPassword(userId: string, newPassword: string): Promise<void> {
  await fetchJson<void>(`${API_BASE_URL}/admin/users/${userId}/password`, {
    method: 'POST',
    body: JSON.stringify({ newPassword })
  });
}
