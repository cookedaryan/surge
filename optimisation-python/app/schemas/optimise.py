from typing import Any, Literal

from pydantic import BaseModel, Field

from app.presentation.models import ProjectOptimizationResult
from app.schemas.v2.optimise import (
    CableConfigRequest,
    CandidateSummary,
    CostingConfigRequest,
    FailuresSummary,
    GenerationSummary,
    LandCommercialContextRequest,
    OperatingPointConfig,
    PoleConfigRequest,
    RecommendationSummary,
    RoutingConfigRequest,
    ScenarioConfigRequest,
    ScoringWeightsRequest,
)

GeoJSON = dict[str, Any]

OptimisationScenario = Literal[
    "Minimum Cost",
    "Minimum Land Impact",
    "Minimum Environmental Impact",
    "Balanced",
]


class ElectricalParams(BaseModel):
    feeder_capacity_mw: float = Field(default=20.0, gt=0)
    max_voltage_drop_pct: float = Field(default=5.0, gt=0, le=100)
    row_width_m: float = Field(default=18.0, gt=0)
    nominal_voltage_kv: float = Field(default=33.0, gt=0)


class OptimisationRequest(BaseModel):
    request_id: str = Field(min_length=1)
    project_id: str = Field(min_length=1)
    scenario: OptimisationScenario

    wtg_geojson: GeoJSON
    substation_geojson: GeoJSON
    avoidance_geojson: GeoJSON | None = None

    electrical_params: ElectricalParams = Field(default_factory=ElectricalParams)
    routing_config: RoutingConfigRequest = Field(
        default_factory=lambda: RoutingConfigRequest(
            resolution_m=10.0,
            padding_m=100.0,
        )
    )
    pole_config: PoleConfigRequest = Field(default_factory=PoleConfigRequest)
    operating_point_config: OperatingPointConfig = Field(
        default_factory=OperatingPointConfig
    )
    cable_config: CableConfigRequest | None = None
    scenario_config: ScenarioConfigRequest = Field(
        default_factory=ScenarioConfigRequest
    )
    scoring_weights: ScoringWeightsRequest = Field(
        default_factory=ScoringWeightsRequest
    )
    # Optional so every existing caller keeps working unchanged. Without it the
    # land engine still runs, but with no commercial profile for any parcel:
    # owner interactions fall back to counting parcels, and no purchase, lease
    # or easement option can be valued.
    land_context: LandCommercialContextRequest | None = None
    # Optional for the same reason, and with a sharper consequence: without it
    # ``evaluate_candidate_cost`` is never called, so every candidate comes back
    # with ``cost: null`` and there is no CAPEX, no loss valuation and no
    # lifecycle figure to compare scenarios on. This model ignores unknown fields,
    # so a caller sending costing_config before it existed here had it silently
    # dropped and got uncosted results with no error to explain them.
    costing_config: CostingConfigRequest | None = None


class OptimisationMetrics(BaseModel):
    feeder_count: int = Field(default=0, ge=0)
    total_length_m: float = Field(default=0.0, ge=0)
    estimated_cost: float | None = Field(default=None, ge=0)
    message: str | None = None


class OptimisationResponse(BaseModel):
    request_id: str
    status: Literal["success", "failed"]
    scenario: OptimisationScenario
    feeder_routes_geojson: GeoJSON | None = None
    poles_geojson: GeoJSON | None = None
    metrics: OptimisationMetrics = Field(default_factory=OptimisationMetrics)
    schema_version: str = "2.0"
    workflow_status: Literal[
        "SUCCESS", "PARTIAL_SUCCESS", "NO_FEASIBLE_CANDIDATE", "FAILED"
    ] = "SUCCESS"
    generation: GenerationSummary | None = None
    candidates: list[CandidateSummary] = Field(default_factory=list)
    recommendation: RecommendationSummary | None = None
    recommended_result: ProjectOptimizationResult | None = None
    failures: list[FailuresSummary] = Field(default_factory=list)
