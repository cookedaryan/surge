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
    route_length_weight: float = Field(default=0.4, ge=0.0, le=1.0)
    electrical_loss_weight: float = Field(default=0.25, ge=0.0, le=1.0)
    cable_loading_weight: float = Field(default=0.20, ge=0.0, le=1.0)
    voltage_margin_weight: float = Field(default=0.15, ge=0.0, le=1.0)

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


class OptimiseProjectRequest(ApiModel):
    request_id: str = Field(min_length=1)
    project_id: str = Field(min_length=1)

    wtg_geojson: GeoJSON
    substation_geojson: GeoJSON

    routing_config: RoutingConfigRequest = Field(default_factory=RoutingConfigRequest)
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


class GenerationSummary(ApiModel):
    requested_candidate_count: int
    accepted_candidate_count: int
    attempts: int


class CandidateSummary(ApiModel):
    scenario_id: str
    parameter_set_id: str
    strategy: str
    topology_fingerprint: str
    electrical_status: Literal["VALID", "INVALID"] | None = None
    eligible: bool | None = None
    rank: int | None = None
    total_benefit_score: float | None = None
    raw_metrics: dict[str, float] | None = None
    disqualifications: list[str] | None = None
    execution_failure: dict[str, Any] | None = None


class RecommendationSummary(ApiModel):
    recommended_scenario_id: str | None
    normalization_ranges: dict[str, dict[str, float]]
    reasons: list[str]
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
