import { API_BASE_URL, fetchJson } from './client';
import type { AuditLog } from './types';

export async function getAuditLogs(): Promise<AuditLog[]> {
  try {
    return await fetchJson<AuditLog[]>(`${API_BASE_URL}/audit-logs`);
  } catch {
    return [];
  }
}
