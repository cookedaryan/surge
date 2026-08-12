import { API_BASE_URL, fetchJson } from './client';
import type { BomReport, ScenarioComparison } from './types';

export async function getBomReport(projectId: string): Promise<BomReport> {
  try {
    return await fetchJson<BomReport>(`${API_BASE_URL}/projects/${projectId}/reports/bom`);
  } catch {
    return {
      totalNetworkLengthMeters: 0,
      totalPoles: 0,
      totalEstimatedCost: 0,
      totalElectricalLossesKw: 0,
      feederSummaries: []
    };
  }
}

export function getPdfReportUrl(projectId: string): string {
  return `${API_BASE_URL}/projects/${projectId}/reports/pdf`;
}

export function getBomCsvUrl(projectId: string, jobId?: string | null): string {
  if (jobId) return `${API_BASE_URL}/projects/${projectId}/jobs/${jobId}/reports/bom/csv`;
  return `${API_BASE_URL}/projects/${projectId}/reports/bom/csv`;
}

export async function getScenarioComparison(projectId: string): Promise<ScenarioComparison> {
  return await fetchJson<ScenarioComparison>(`${API_BASE_URL}/projects/${projectId}/reports/scenarios/compare`);
}
