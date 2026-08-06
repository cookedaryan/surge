from typing import Any, Literal

from pydantic import BaseModel, Field

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


class OptimisationRequest(BaseModel):
    request_id: str = Field(min_length=1)
    project_id: str = Field(min_length=1)
    scenario: OptimisationScenario

    wtg_geojson: GeoJSON
    substation_geojson: GeoJSON

    electrical_params: ElectricalParams = Field(
        default_factory=ElectricalParams
    )


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
    metrics: OptimisationMetrics = Field(
        default_factory=OptimisationMetrics
    )
