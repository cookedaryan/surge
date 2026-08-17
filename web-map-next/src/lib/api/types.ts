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

export type UserRole = 'ROLE_ADMIN' | 'ROLE_ENGINEER' | 'ROLE_VIEWER';

/** An account as returned by the admin API. Carries no password material. */
export interface AdminUser {
  id: string;
  username: string;
  email: string;
  role: UserRole;
  enabled: boolean;
  createdAt: string;
}

export interface Job {
  id: string;
  status?: string;
  scenario?: string;
  errorMessage?: string;
  resultSummaryJson?: string;
}

/**
 * What the engine measured on one candidate network.
 *
 * <p>These are the figures the ranking is computed from, so they are also the only honest way to
 * show what the recommendation beat: absolute values an engineer can compare directly, rather than
 * a claim about which direction is "better" on each metric.
 */
export interface CandidateEngineeringMetrics {
  total_route_length_m?: number;
  total_traversal_cost?: number;
  physical_pole_count?: number;
  total_active_loss_mw?: number;
  maximum_loading_percent?: number;
  voltage_margin_pu?: number;
  road_crossing_count?: number;
  affected_parcel_count?: number;
  owner_interaction_count?: number;
  soft_constraint_overlap_length_m?: number;
  environmental_overlap_m2?: number;
}

/** One conductor upgrade the repair loop tried, with the loading it moved. */
export interface RepairAttempt {
  segment_id?: string | null;
  iteration?: number | null;
  from_cable_type_id?: string | null;
  to_cable_type_id?: string | null;
  trigger_violation_type?: string | null;
  reason_code?: string | null;
  pre_repair_loading_pct?: number | null;
  post_repair_loading_pct?: number | null;
  pre_repair_voltage_pu?: number | null;
  post_repair_voltage_pu?: number | null;
}

/** The biggest conductor the catalogue had, which is the ceiling repair was working against. */
export interface LargestCableAvailable {
  cable_type_id?: string | null;
  effective_ampacity_a?: number | null;
  parallel_count?: number | null;
}

/**
 * Why electrical repair gave up.
 *
 * <p>Without this a failed run said `REPAIR_EXHAUSTED` and nothing else, leaving no way to tell an
 * undersized catalogue from a design no conductor can fix.
 */
export interface RepairDiagnostics {
  status?: string;
  summary?: string;
  /**
   * Why no conductor upgrade was made, when none was.
   *
   * <p>An empty `repair_attempts` reads the same whether the catalogue ran out of current or the
   * violation was one no conductor choice can address — and those want opposite responses.
   */
  no_upgrade_reason?: string | null;
  no_upgrade_reason_code?: string | null;
  unresolved_violations?: ElectricalViolation[];
  repair_attempts?: RepairAttempt[];
  largest_cable_available?: LargestCableAvailable | null;
  catalogue_size?: number;
}

export interface CandidateExecutionFailure {
  code?: string;
  message?: string;
  stage?: string | null;
  details?: RepairDiagnostics | null;
}

export interface CandidateGroupScore {
  group: string;
  group_score: number;
  group_weight: number;
  weighted_score: number;
}

export interface CandidateSummary {
  scenario_id: string;
  strategy?: string;
  electrical_status?: 'VALID' | 'INVALID';
  eligible?: boolean;
  rank?: number;
  total_benefit_score?: number | null;
  engineering_metrics?: CandidateEngineeringMetrics | null;
  execution_failure?: CandidateExecutionFailure | null;
  disqualifications?: string[];
  group_scores?: CandidateGroupScore[] | null;
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

/** One feeder's electrical result. The network summary reports only the totals. */
export interface FeederElectricalResult {
  feeder_id: string;
  wtg_count?: number;
  segment_count?: number;
  route_length_m?: number;
  active_loss_mw?: number | null;
  reactive_loss_mvar?: number | null;
  minimum_voltage_pu?: number | null;
  maximum_voltage_pu?: number | null;
  maximum_loading_percent?: number | null;
  valid?: boolean;
}

/**
 * A breached limit, with the value that breached it.
 *
 * <p>The electrical summary carries a violation *count*, which says something is wrong without
 * saying where — so this is what turns "1 violation" into somewhere to look.
 */
export interface ElectricalViolation {
  code: string;
  message: string;
  scope?: string;
  node_id?: string | null;
  segment_id?: string | null;
  feeder_id?: string | null;
  measured_value?: number | null;
  limit_value?: number | null;
}

export interface RecommendationReasonSummary {
  code: string;
  message: string;
  metric?: string | null;
  candidate_value?: number | null;
  comparison_value?: number | null;
}

export interface JobDecisionSummary {
  workflowStatus?: string;
  candidates?: CandidateSummary[];
  recommendation?: {
    recommended_scenario_id?: string | null;
    reasons?: string[];
    reason_details?: RecommendationReasonSummary[];
  };
  failures?: { stage: string; code: string; message: string }[];
  networkSummary?: NetworkSummary;
  electricalSummary?: ElectricalSummary;
  feeders?: FeederElectricalResult[];
  violations?: ElectricalViolation[];
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
  /**
   * The network's CAPEX as the engine priced it, or null when the run was not costed.
   *
   * <p>Nullable deliberately. This was a number that fell back to a per-route `length x 80`
   * fabrication, so it was never absent and never had to be read as unknown.
   */
  totalEstimatedCost: number | null;
  /** ISO 4217 code for the figures here, or null when the run was not costed. */
  costCurrency?: string | null;
  /**
   * Components the engine could not price.
   *
   * <p>Above zero, `totalEstimatedCost` is a partial sum: the engine omits a component it cannot
   * price rather than pricing it at zero.
   */
  costFailureCount?: number | null;
  conductorCapex: number | null;
  poleCapex: number | null;
  landCapex: number | null;
  annualLossEnergyMwh: number | null;
  annualLossCost: number | null;
  presentValueOpex: number | null;
  lifecycleCost: number | null;
  totalElectricalLossesKw: number;
  rowWidthMeters: number;
  totalAffectedAreaM2: number;
  totalCompensationCost: number;
  poleCountByRole: Record<string, number>;
  poleCountByType: Record<string, number>;
  feederSummaries: FeederBomSummary[];
  segmentDetails: RouteSegmentDetail[];
  poleSchedule: unknown[];
  ownerInteractionCount: number | null;
  ownerInteractionBasis: string | null;
  landCostBasis: string | null;
  landIsFeasible: boolean | null;
  parcelImpactSummaries: ParcelImpactSummary[];
}

export interface ParcelImpactSummary {
  parcelId: string;
  ownerName?: string;
  ownerId?: string | null;
  acquisitionCostPerM2: number;
  affectedAreaM2: number;
  estimatedCompensationCost: number;
  availabilityStatus?: string | null;
  transactionMode?: string | null;
  selectedPresentValue?: number | null;
  priceBasis?: string | null;
  priceDate?: string | null;
}

export interface FeederBomSummary {
  feederName: string;
  segmentCount: number;
  lengthMeters: number;
  poleCount: number;
  electricalLossesKw: number;
}

export interface RouteSegmentDetail {
  feederName: string;
  segmentId: string;
  lengthMeters: number;
  poleCount: number;
  conductorCost: number | null;
  electricalLossesKw: number;
  cableTypeId: string;
  cableParallelCount: number;
  cableDeratingFactor: number;
  cableUtilisationPct: number;
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
