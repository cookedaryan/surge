import { API_BASE_URL, downloadFile, fetchJson } from './client';
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

/** Both exports go through an authenticated fetch; see {@link downloadFile}. */
export async function downloadBomCsv(projectId: string, jobId?: string | null): Promise<void> {
  await downloadFile(getBomCsvUrl(projectId, jobId), `surge-bom-${projectId}.csv`);
}

export async function downloadPdfReport(projectId: string): Promise<void> {
  await downloadFile(getPdfReportUrl(projectId), `surge-executive-report-${projectId}.pdf`);
}

export async function getScenarioComparison(projectId: string): Promise<ScenarioComparison> {
  return await fetchJson<ScenarioComparison>(`${API_BASE_URL}/projects/${projectId}/reports/scenarios/compare`);
}
