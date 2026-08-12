import type { FeatureCollection } from 'geojson';
export type { FeatureCollection };

export interface Project {
  id: string;
  name: string;
  description?: string;
  crs?: string;
  createdAt?: string;
}

export interface AuthResponse {
  token: string;
  username: string;
  role: string;
}

export interface Job {
  id: string;
  status?: string;
}

export interface JobProgress {
  status: string;
  progressPercent?: number;
  message?: string;
}

export interface OptimizationParams {
  scenario: string;
  feederCapacityMw: number;
  maxSpanMeters: number;
  voltageKv: number;
}

export interface BomReport {
  totalNetworkLengthMeters: number;
  totalPoles: number;
  totalEstimatedCost: number;
  totalElectricalLossesKw: number;
  feederSummaries: unknown[];
}

export interface ImportPreviewFeature {
  externalId: string;
  geometryType: string;
  kmlFolder?: string;
  classifiedAs?: string;
  lineType?: string;
  status?: string;
  matchedRule: string;
  evidence?: string;
  vertexCount?: number;
}

export interface ImportPreview {
  importId: string;
  fileName?: string;
  countsByType?: Record<string, number>;
  duplicatesRemoved?: number;
  skippedByGeometry?: Record<string, number>;
  features: ImportPreviewFeature[];
}

export interface CommitImportBody {
  importId: string;
  overrides: Record<string, string>;
  defaultCapacityMw: number | null;
  skipUnclassified: boolean;
}

export interface CommitImportResult {
  wtgsImported?: number;
  substationsImported?: number;
  towersImported?: number;
  unclassified?: number;
}

export interface AuditLog {
  username?: string;
  action: string;
  details?: string;
  resourceType?: string;
  timestamp?: string;
}

export interface ScenarioComparisonEntry {
  scenarioName: string;
  totalEstimatedCost?: number;
  totalElectricalLossesKw?: number;
  landRowCompensationCost?: number;
  totalNetworkLengthMeters?: number;
  totalPoles?: number;
  capexDeltaPct?: number;
  lossesDeltaPct?: number;
}

export interface ScenarioComparison {
  scenarios: ScenarioComparisonEntry[];
}
