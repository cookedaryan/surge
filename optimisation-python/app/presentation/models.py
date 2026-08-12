"""Pydantic presentation models for the Surge result boundary.

These models define the explicit JSON and API contract for a successfully
optimised and evaluated project. They are not used for internal routing
or electrical calculation.
"""

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict


class PresentationModel(BaseModel):
    """Strict base for the public JSON boundary."""

    model_config = ConfigDict(
        allow_inf_nan=False,
        extra="forbid",
        frozen=True,
    )


class NetworkSummary(PresentationModel):
    wtg_count: int
    feeder_count: int
    segment_count: int
    total_route_length_m: float


class ElectricalSummary(PresentationModel):
    converged: bool
    valid: bool
    solver_algorithm: str | None
    total_active_loss_mw: float | None
    total_reactive_loss_mvar: float | None
    minimum_voltage_pu: float | None
    maximum_voltage_pu: float | None
    maximum_loading_percent: float | None
    violation_count: int


class ViolationPresentation(PresentationModel):
    code: str
    message: str
    scope: Literal["network", "feeder", "node", "segment"]
    node_id: str | None = None
    segment_id: str | None = None
    feeder_id: str | None = None
    measured_value: float | None = None
    limit_value: float | None = None


class FeederResult(PresentationModel):
    feeder_id: str
    wtg_ids: list[str]
    segment_ids: list[str]
    wtg_count: int
    segment_count: int
    route_length_m: float
    active_loss_mw: float | None
    reactive_loss_mvar: float | None
    minimum_voltage_pu: float | None
    maximum_voltage_pu: float | None
    maximum_loading_percent: float | None
    valid: bool
    violations: list[ViolationPresentation]


class ProjectOptimizationResult(PresentationModel):
    schema_version: str = "1.0.0"
    project_id: str
    network_summary: NetworkSummary
    electrical_summary: ElectricalSummary
    feeders: list[FeederResult]
    violations: list[ViolationPresentation]
    feature_collection: dict[str, Any]
    source_crs: str
