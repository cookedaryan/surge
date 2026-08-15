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
  scenario?: string;
  errorMessage?: string;
  resultSummaryJson?: string;
}

export interface CandidateSummary {
  scenario_id: string;
  strategy?: string;
  electrical_status?: 'VALID' | 'INVALID';
  eligible?: boolean;
  rank?: number;
  disqualifications?: string[];
}

export interface ElectricalSummary {
  converged: boolean;
  valid: boolean;
  solver_algorithm?: string | null;
  total_active_loss_mw?: number | null;
  total_reactive_loss_mvar?: number | null;
  minimum_voltage_pu?: number | null;
  maximum_voltage_pu?: number | null;
  maximum_loading_percent?: number | null;
  violation_count: number;
}

export interface NetworkSummary {
  wtg_count: number;
  feeder_count: number;
  segment_count: number;
  total_route_length_m: number;
}

export interface PoleSummary {
  total_poles: number;
  terminal_poles: number;
  angle_poles: number;
  intermediate_poles: number;
  junction_poles: number;
}

export interface SpatialConstraintSummary {
  hard_exclusion_violation_count: number;
  soft_constraint_intersection_count: number;
  soft_constraint_overlap_length_m: number;
  road_crossing_count: number;
  affected_parcel_count: number;
  affected_parcel_overlap_length_m: number;
}

export interface JobDecisionSummary {
  workflowStatus?: string;
  candidates?: CandidateSummary[];
  recommendation?: { recommended_scenario_id?: string | null; reasons?: string[] };
  failures?: { stage: string; code: string; message: string }[];
  networkSummary?: NetworkSummary;
  electricalSummary?: ElectricalSummary;
  poleSummary?: PoleSummary;
  spatialConstraintSummary?: SpatialConstraintSummary;
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
