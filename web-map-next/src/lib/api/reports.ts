import { API_BASE_URL, downloadFile, fetchJson } from './client';
import type { BomReport, ScenarioComparison } from './types';

/**
 * The BOM for one specific run.
 *
 * <p>Unlike {@link getBomReport} this throws rather than returning a zeroed report. It backs the
 * run breakdown, where the costs sit beside the decision that produced them: a silently empty BOM
 * there would read as a network that costs nothing, next to figures saying otherwise.
 */
export async function getJobBomReport(projectId: string, jobId: string): Promise<BomReport> {
  return fetchJson<BomReport>(`${API_BASE_URL}/projects/${projectId}/reports/jobs/${jobId}/bom`);
}

export async function getBomReport(projectId: string): Promise<BomReport> {
  try {
    return await fetchJson<BomReport>(`${API_BASE_URL}/projects/${projectId}/reports/bom`);
  } catch {
    return {
      totalNetworkLengthMeters: 0,
      totalPoles: 0,
      // Null, not 0: a report that could not be fetched has an unknown cost, and a zero would read
      // as a free network.
      totalEstimatedCost: null,
      conductorCapex: null,
      poleCapex: null,
      landCapex: null,
      annualLossEnergyMwh: null,
      annualLossCost: null,
      presentValueOpex: null,
      lifecycleCost: null,
      totalElectricalLossesKw: 0,
      rowWidthMeters: 0,
      totalAffectedAreaM2: 0,
      totalCompensationCost: 0,
      poleCountByRole: {},
      poleCountByType: {},
      feederSummaries: [],
      segmentDetails: [],
      poleSchedule: [],
      ownerInteractionCount: null,
      ownerInteractionBasis: null,
      landCostBasis: null,
      landIsFeasible: null,
      parcelImpactSummaries: []
    };
  }
}

export function getPdfReportUrl(projectId: string): string {
  return `${API_BASE_URL}/projects/${projectId}/reports/pdf`;
}

export function getBomCsvUrl(projectId: string, jobId?: string | null): string {
  // The job-scoped segment goes *after* /reports, which is where ReportController maps it
  // (@RequestMapping(".../reports") + @GetMapping("/jobs/{jobId}/bom/csv")). Built the other way
  // round this addressed a route no controller serves, so exporting a CSV 404'd for every run —
  // and a run is exactly when currentJobId is set, which is to say always after the first one.
  if (jobId) return `${API_BASE_URL}/projects/${projectId}/reports/jobs/${jobId}/bom/csv`;
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
