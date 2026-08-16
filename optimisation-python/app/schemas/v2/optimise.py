import math
from typing import Any, Literal, Self

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.presentation.models import ProjectOptimizationResult

GeoJSON = dict[str, Any]


class ApiModel(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
        allow_inf_nan=False,
        str_strip_whitespace=True,
    )


class RoutingConfigRequest(ApiModel):
    resolution_m: float = Field(default=20.0, ge=5.0, le=100.0)
    padding_m: float = Field(default=1000.0, ge=0.0, le=5000.0)
    avoidance_buffer_m: float = Field(default=10.0, ge=0.0, le=500.0)
    avoidance_cost_weight: float = Field(default=20.0, gt=0.0, le=1_000_000.0)
    row_width_m: float = Field(default=18.0, gt=0.0, le=500.0)


class PoleConfigRequest(ApiModel):
    target_span_m: float = Field(default=100.0, gt=0.0, le=500.0)
    min_span_m: float = Field(default=30.0, gt=0.0, le=500.0)
    max_span_m: float = Field(default=120.0, gt=0.0, le=500.0)
    angle_pole_threshold_deg: float = Field(default=10.0, ge=0.0, le=180.0)

    @model_validator(mode="after")
    def validate_spans(self) -> Self:
        if self.min_span_m > self.max_span_m:
            raise ValueError("min_span_m must not exceed max_span_m")
        if self.target_span_m > self.max_span_m:
            raise ValueError("target_span_m must not exceed max_span_m")
        return self


class OperatingPointConfig(ApiModel):
    operating_factor: float = Field(default=1.0, ge=0.0, le=1.0)
    power_factor: float = Field(default=0.95, gt=0.0, le=1.0)
    power_factor_mode: Literal["lagging", "leading"] = "lagging"


class CableTypeRequest(ApiModel):
    cable_type_id: str = Field(min_length=1)
    resistance_ohm_per_km: float = Field(ge=0.0)
    reactance_ohm_per_km: float = Field(ge=0.0)
    capacitance_nf_per_km: float = Field(ge=0.0)
    max_current_a: float = Field(gt=0.0)
    parallel_count: int = Field(default=1, ge=1)
    derating_factor: float = Field(default=1.0, gt=0.0, le=1.0)


class CableConfigRequest(ApiModel):
    nominal_voltage_kv: float = Field(gt=0.0)
    slack_voltage_pu: float = Field(default=1.0, gt=0.0)
    min_voltage_pu: float = Field(default=0.95, gt=0.0)
    max_voltage_pu: float = Field(default=1.05, gt=0.0)
    system_base_mva: float = Field(default=100.0, gt=0.0)
    cable_types: list[CableTypeRequest] = Field(min_length=1)
    default_cable_type_id: str = Field(min_length=1)

    @model_validator(mode="after")
    def validate_cable_configuration(self) -> Self:
        if self.min_voltage_pu >= self.max_voltage_pu:
            raise ValueError("min_voltage_pu must be strictly less than max_voltage_pu")

        cable_ids = [cable.cable_type_id for cable in self.cable_types]
        if len(cable_ids) != len(set(cable_ids)):
            raise ValueError("cable_type_id values must be unique")
        if self.default_cable_type_id not in cable_ids:
            raise ValueError(
                "default_cable_type_id must reference a configured cable type"
            )
        return self


class ScenarioConfigRequest(ApiModel):
    candidate_count: int = Field(default=3, ge=1, le=5)


class ScoringWeightsRequest(ApiModel):
    route_length_weight: float = Field(default=0.4, ge=0.0, le=1.0, strict=True)
    electrical_loss_weight: float = Field(default=0.25, ge=0.0, le=1.0, strict=True)
    cable_loading_weight: float = Field(default=0.20, ge=0.0, le=1.0, strict=True)
    voltage_margin_weight: float = Field(default=0.15, ge=0.0, le=1.0, strict=True)

    @model_validator(mode="after")
    def validate_weight_total(self) -> Self:
        total = math.fsum(
            (
                self.route_length_weight,
                self.electrical_loss_weight,
                self.cable_loading_weight,
                self.voltage_margin_weight,
            )
        )
        if not math.isclose(total, 1.0, rel_tol=1e-9, abs_tol=1e-9):
            raise ValueError(f"scoring weights must sum to 1.0, got {total}")
        return self


class SpatialScoringWeightsRequest(ApiModel):
    traversal_cost: float = Field(default=0.4, ge=0.0, le=1.0, strict=True)
    affected_parcels: float = Field(default=0.3, ge=0.0, le=1.0, strict=True)
    road_crossings: float = Field(default=0.2, ge=0.0, le=1.0, strict=True)
    soft_overlap_length: float = Field(default=0.1, ge=0.0, le=1.0, strict=True)


class ElectricalScoringWeightsRequest(ApiModel):
    active_loss: float = Field(default=0.45, ge=0.0, le=1.0, strict=True)
    cable_loading: float = Field(default=0.35, ge=0.0, le=1.0, strict=True)
    voltage_margin: float = Field(default=0.20, ge=0.0, le=1.0, strict=True)


class EngineeringScoringWeightsRequest(ApiModel):
    physical_weight: float = Field(default=0.3, ge=0.0, le=1.0, strict=True)
    spatial_weight: float = Field(default=0.3, ge=0.0, le=1.0, strict=True)
    infrastructure_weight: float = Field(default=0.15, ge=0.0, le=1.0, strict=True)
    electrical_weight: float = Field(default=0.25, ge=0.0, le=1.0, strict=True)

    spatial_subweights: SpatialScoringWeightsRequest = Field(
        default_factory=SpatialScoringWeightsRequest
    )
    electrical_subweights: ElectricalScoringWeightsRequest = Field(
        default_factory=ElectricalScoringWeightsRequest
    )

    @model_validator(mode="after")
    def validate_weight_total(self) -> Self:
        total = math.fsum(
            (
                self.physical_weight,
                self.spatial_weight,
                self.infrastructure_weight,
                self.electrical_weight,
            )
        )
        if not math.isclose(total, 1.0, rel_tol=1e-9, abs_tol=1e-9):
            raise ValueError(f"group weights must sum to 1.0, got {total}")

        self._validate_subweights(
            self.spatial_weight,
            (
                self.spatial_subweights.traversal_cost,
                self.spatial_subweights.affected_parcels,
                self.spatial_subweights.road_crossings,
                self.spatial_subweights.soft_overlap_length,
            ),
            "spatial",
        )
        self._validate_subweights(
            self.electrical_weight,
            (
                self.electrical_subweights.active_loss,
                self.electrical_subweights.cable_loading,
                self.electrical_subweights.voltage_margin,
            ),
            "electrical",
        )
        return self

    @staticmethod
    def _validate_subweights(
        group_weight: float, subweights: tuple[float, ...], group_name: str
    ) -> None:
        total = math.fsum(subweights)
        if group_weight > 0.0:
            if not math.isclose(total, 1.0, rel_tol=1e-9, abs_tol=1e-9):
                raise ValueError(
                    f"active {group_name} subweights must sum to 1.0, got {total}"
                )
        elif any(weight != 0.0 for weight in subweights):
            raise ValueError(
                f"inactive {group_name} group must have exactly 0.0 subweights"
            )


class CostAwareRecommendationConfigRequest(ApiModel):
    engineering_weight: float = Field(default=0.7, ge=0.0, le=1.0, strict=True)
    lifecycle_cost_weight: float = Field(default=0.3, ge=0.0, le=1.0, strict=True)

    @model_validator(mode="after")
    def validate_weight_total(self) -> Self:
        total = math.fsum((self.engineering_weight, self.lifecycle_cost_weight))
        if not math.isclose(total, 1.0, rel_tol=1e-9, abs_tol=1e-9):
            raise ValueError(f"cost-aware weights must sum to 1.0, got {total}")
        return self


class ConductorCostItemRequest(ApiModel):
    cable_type_id: str = Field(min_length=1)
    installed_cost_per_km_per_parallel_circuit: float = Field(ge=0.0)


class PoleCostItemRequest(ApiModel):
    pole_type: Literal["terminal", "angle", "intermediate", "junction"]
    installed_cost_each: float = Field(ge=0.0)


class LandCostPolicyRequest(ApiModel):
    fixed_cost_per_affected_parcel: float = Field(ge=0.0)
    variable_basis: Literal[
        "NONE",
        "ROUTE_OVERLAP_LENGTH_M",
        "ROW_INTERSECTION_AREA_M2",
    ]
    variable_rate: float = Field(ge=0.0)


class EngineeringCostCatalogueRequest(ApiModel):
    catalogue_id: str = Field(min_length=1)
    version: str = Field(min_length=1)
    currency: str = Field(min_length=3, max_length=3)
    price_basis_date: str
    conductor_items: list[ConductorCostItemRequest]
    pole_items: list[PoleCostItemRequest]
    land_policy: LandCostPolicyRequest


class LifecycleCostConfigRequest(ApiModel):
    currency: str = Field(min_length=3, max_length=3)
    energy_price_basis_date: str
    analysis_period_years: int = Field(ge=1)
    discount_rate: float = Field(ge=0.0, lt=1.0)
    annual_operating_hours: int = Field(ge=0, le=8760)
    loss_load_factor: float = Field(ge=0.0, le=1.0)
    energy_price_per_mwh: float = Field(ge=0.0)


class CostingConfigRequest(ApiModel):
    catalogue: EngineeringCostCatalogueRequest
    lifecycle: LifecycleCostConfigRequest


class OptimiseProjectRequest(ApiModel):
    request_id: str = Field(min_length=1)
    project_id: str = Field(min_length=1)

    wtg_geojson: GeoJSON
    substation_geojson: GeoJSON
    avoidance_geojson: GeoJSON | None = None

    routing_config: RoutingConfigRequest = Field(default_factory=RoutingConfigRequest)
    pole_config: PoleConfigRequest | None = None
    operating_point_config: OperatingPointConfig = Field(
        default_factory=OperatingPointConfig
    )
    cable_config: CableConfigRequest
    scenario_config: ScenarioConfigRequest = Field(
        default_factory=ScenarioConfigRequest
    )
    scoring_weights: ScoringWeightsRequest = Field(
        default_factory=ScoringWeightsRequest
    )
    engineering_scoring_weights: EngineeringScoringWeightsRequest | None = None
    costing_config: CostingConfigRequest | None = None
    cost_aware_config: CostAwareRecommendationConfigRequest | None = None

    @model_validator(mode="after")
    def validate_policy_and_pole_config(self) -> Self:
        explicit_legacy = "scoring_weights" in self.model_fields_set
        explicit_unified = self.engineering_scoring_weights is not None

        if explicit_legacy and explicit_unified:
            raise ValueError(
                "Cannot explicitly supply both scoring_weights "
                "and engineering_scoring_weights"
            )

        if explicit_unified and self.pole_config is None:
            raise ValueError(
                "pole_config is required when using engineering_scoring_weights"
            )

        if self.cost_aware_config is not None and self.costing_config is None:
            raise ValueError("costing_config is required when using cost_aware_config")

        return self


class GenerationSummary(ApiModel):
    requested_candidate_count: int
    accepted_candidate_count: int
    attempts: int


class EngineeringMetricsSummary(ApiModel):
    total_route_length_m: float
    total_traversal_cost: float
    affected_parcel_count: int
    road_crossing_count: int
    soft_constraint_overlap_length_m: float
    environmental_overlap_m2: float
    physical_pole_count: int
    total_active_loss_mw: float
    maximum_loading_percent: float
    voltage_margin_pu: float


class GroupScoreSummary(ApiModel):
    group: str
    group_score: float
    group_weight: float
    weighted_score: float


class RecommendationReasonSummary(ApiModel):
    code: str
    message: str
    metric: str | None = None
    candidate_value: float | None = None
    comparison_value: float | None = None


class CostLineItemSummary(ApiModel):
    category: str
    item_id: str
    quantity: float
    unit: str
    unit_rate: float
    amount: float


class CostFailureSummary(ApiModel):
    code: str
    component: str
    message: str
    item_id: str | None = None
    segment_id: str | None = None
    pole_id: str | None = None


class CandidateCostSummary(ApiModel):
    conductor_capex: float | None = None
    pole_capex: float | None = None
    land_purchase_capex: float | None = None
    total_capex: float | None = None
    land_recurring_cost_pv: float | None = None
    land_access_present_value: float | None = None
    annual_loss_energy_mwh: float | None = None
    annual_loss_cost: float | None = None
    present_value_factor: float | None = None
    present_value_opex: float | None = None
    lifecycle_cost: float | None = None
    line_items: list[CostLineItemSummary] | None = None
    currency: str | None = None
    catalogue_id: str | None = None
    catalogue_version: str | None = None
    catalogue_price_basis_date: str | None = None
    energy_price_basis_date: str | None = None
    cost_model_version: str | None = None
    failures: list[CostFailureSummary] = Field(default_factory=list)


class CandidateSummary(ApiModel):
    scenario_id: str
    parameter_set_id: str
    strategy: str
    topology_fingerprint: str
    electrical_status: Literal["VALID", "INVALID"] | None = None
    eligible: bool | None = None
    rank: int | None = None
    engineering_benefit_score: float | None = None
    economic_benefit_score: float | None = None
    final_benefit_score: float | None = None
    total_benefit_score: float | None = None
    raw_metrics: dict[str, float] | None = None
    engineering_metrics: EngineeringMetricsSummary | None = None
    cost: CandidateCostSummary | None = None
    group_scores: list[GroupScoreSummary] | None = None
    disqualifications: list[str] | None = None
    execution_failure: dict[str, Any] | None = None
    cable_sizing: dict[str, Any] | None = None


class RecommendationSummary(ApiModel):
    recommended_scenario_id: str | None = None
    engineering_best_scenario_id: str | None = None
    lowest_cost_scenario_id: str | None = None
    policy: str | None = None
    economic_context_id: str | None = None
    normalization_ranges: dict[str, dict[str, float]]
    reasons: list[str]
    reason_details: list[RecommendationReasonSummary]
    baseline_comparisons: dict[str, float]


class FailuresSummary(ApiModel):
    stage: str
    code: str
    message: str
    scenario_id: str | None = None


class OptimiseProjectResponse(ApiModel):
    schema_version: str = "2.0"
    request_id: str
    project_id: str
    status: Literal["SUCCESS", "PARTIAL_SUCCESS", "NO_FEASIBLE_CANDIDATE", "FAILED"]

    generation: GenerationSummary | None = None
    candidates: list[CandidateSummary] = Field(default_factory=list)
    recommendation: RecommendationSummary | None = None
    recommended_result: ProjectOptimizationResult | None = None
    failures: list[FailuresSummary] = Field(default_factory=list)
