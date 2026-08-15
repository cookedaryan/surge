"""In-memory candidate evaluation caching and contextual fingerprinting."""

import hashlib
import json
from dataclasses import dataclass, replace
from typing import Any

from app.costing.models import CandidateCostAssessment
from app.electrical.cable_sizing import CableSizingResult
from app.electrical.load_flow.models import LoadFlowNetworkResult
from app.electrical.repair import RepairAction
from app.optimisation.engineering_metric_models import CandidateEngineeringAssessment
from app.optimisation.scenario_models import PNCScenario
from app.optimisation.workflow_models import (
    CandidateFailure,
    CandidateWorkflowResult,
    OptimisationConfig,
    ProjectInput,
)

CacheKey = tuple[str, str]


@dataclass(frozen=True)
class CandidateEvaluationOutcome:
    """Scenario-independent result of the expensive evaluation pipeline."""

    load_flow_result: LoadFlowNetworkResult | None
    engineering_assessment: CandidateEngineeringAssessment | None
    cost_assessment: CandidateCostAssessment | None
    cable_sizing: CableSizingResult | None
    repair_log: tuple[RepairAction, ...]
    execution_failure: CandidateFailure | None

    @classmethod
    def from_candidate(
        cls, candidate: CandidateWorkflowResult
    ) -> "CandidateEvaluationOutcome":
        return cls(
            load_flow_result=candidate.load_flow_result,
            engineering_assessment=candidate.engineering_assessment,
            cost_assessment=candidate.cost_assessment,
            cable_sizing=candidate.cable_sizing,
            repair_log=candidate.repair_log,
            execution_failure=candidate.execution_failure,
        )

    def to_candidate(self, scenario: PNCScenario) -> CandidateWorkflowResult:
        """Bind a cached evaluation to a materialized scenario identity."""
        scenario_id = scenario.scenario_id
        failure = (
            replace(self.execution_failure, scenario_id=scenario_id)
            if self.execution_failure
            else None
        )
        engineering = (
            replace(self.engineering_assessment, scenario_id=scenario_id)
            if self.engineering_assessment
            else None
        )
        cost = self.cost_assessment
        if cost:
            lifecycle_cost = (
                replace(cost.cost, scenario_id=scenario_id) if cost.cost else None
            )
            cost = replace(cost, scenario_id=scenario_id, cost=lifecycle_cost)

        return CandidateWorkflowResult(
            scenario=scenario,
            load_flow_result=self.load_flow_result,
            evaluation=None,
            execution_failure=failure,
            engineering_assessment=engineering,
            cost_assessment=cost,
            cable_sizing=self.cable_sizing,
            repair_log=self.repair_log,
        )


class CandidateEvaluationCache:
    """In-memory cache keyed by design and complete evaluation context."""

    def __init__(self, max_entries: int = 1024) -> None:
        if isinstance(max_entries, bool) or not isinstance(max_entries, int):
            raise ValueError("max_entries must be a positive integer")
        if max_entries < 1:
            raise ValueError("max_entries must be a positive integer")
        self._max_entries = max_entries
        self._cache: dict[CacheKey, CandidateEvaluationOutcome] = {}

    def get(
        self, candidate_fingerprint: str, evaluation_context_id: str
    ) -> CandidateEvaluationOutcome | None:
        return self._cache.get((candidate_fingerprint, evaluation_context_id))

    def put(
        self,
        candidate_fingerprint: str,
        evaluation_context_id: str,
        outcome: CandidateEvaluationOutcome,
    ) -> None:
        key = (candidate_fingerprint, evaluation_context_id)
        if key not in self._cache and len(self._cache) == self._max_entries:
            oldest_key = next(iter(self._cache))
            del self._cache[oldest_key]
        self._cache[key] = outcome


def compute_candidate_evaluation_fingerprint(scenario: PNCScenario) -> str:
    """Hash the fully routed network consumed by candidate evaluation."""
    network = scenario.network
    state = {
        "schema_version": "v1",
        "project_id": network.project_id,
        "substation_id": network.substation_id,
        "substation_geometry_wkb": network.substation_geometry.wkb_hex,
        "crs": network.crs.to_wkt(),
        "wtg_coordinates": sorted(
            (node_id, point.wkb_hex)
            for node_id, point in network.wtg_coordinates.items()
        ),
        "feeders": [
            {
                "feeder_id": feeder.feeder_id,
                "substation_id": feeder.substation_id,
                "wtg_ids": sorted(feeder.wtg_ids),
                "mst_edges": sorted(
                    tuple(sorted((str(first), str(second))))
                    for first, second in feeder.mst_graph.edges
                ),
                "segments": [
                    {
                        "segment_id": segment.segment_id,
                        "from_node_id": segment.from_node_id,
                        "to_node_id": segment.to_node_id,
                        "route_geometry_wkb": segment.route_geometry.wkb_hex,
                        "route_length_m": segment.route_length_m,
                        "traversal_cost": segment.traversal_cost,
                        "segment_type": segment.segment_type,
                    }
                    for segment in sorted(
                        feeder.segments, key=lambda item: item.segment_id
                    )
                ],
            }
            for feeder in sorted(network.feeders, key=lambda item: item.feeder_id)
        ],
    }
    serialized = json.dumps(
        state,
        allow_nan=False,
        separators=(",", ":"),
        sort_keys=True,
    )
    return hashlib.sha256(serialized.encode("utf-8")).hexdigest()


def compute_evaluation_context_id(
    project_input: ProjectInput,
    config: OptimisationConfig,
    electrical_context_id: str,
) -> str:
    """Hash every non-topological input used to evaluate and score a design."""
    state: dict[str, Any] = {
        "pipeline_version": "v1",
        "project_id": project_input.project_id,
        "electrical_context_id": electrical_context_id,
        "row_width_m": project_input.row_width_m,
        "constraint_layers": [
            {
                "layer_id": layer.layer_id,
                "layer_type": layer.layer_type.value,
                "mode": layer.mode.value,
                "geometry_wkb": layer.geometry.wkb_hex,
                "buffer_m": layer.buffer_m,
                "cost_weight": layer.cost_weight,
                "crs": layer.crs.to_wkt(),
            }
            for layer in sorted(
                project_input.constraint_layers, key=lambda item: item.layer_id
            )
        ],
        "pole": (
            {
                "max_span_m": config.pole.max_span_m,
                "min_span_m": config.pole.min_span_m,
                "target_span_m": config.pole.target_span_m,
                "angle_pole_threshold_deg": config.pole.angle_pole_threshold_deg,
                "coordinate_tolerance_m": config.pole.coordinate_tolerance_m,
            }
            if config.pole
            else None
        ),
        "scoring": {
            "policy_mode": config.scoring.policy_mode.value,
            "physical_weight": config.scoring.physical_weight,
            "spatial_weight": config.scoring.spatial_weight,
            "infrastructure_weight": config.scoring.infrastructure_weight,
            "electrical_weight": config.scoring.electrical_weight,
            "spatial_subweights": {
                "traversal_cost": config.scoring.spatial_subweights.traversal_cost,
                "affected_parcels": config.scoring.spatial_subweights.affected_parcels,
                "road_crossings": config.scoring.spatial_subweights.road_crossings,
                "soft_overlap_length": (
                    config.scoring.spatial_subweights.soft_overlap_length
                ),
            },
            "electrical_subweights": {
                "active_loss": config.scoring.electrical_subweights.active_loss,
                "cable_loading": config.scoring.electrical_subweights.cable_loading,
                "voltage_margin": config.scoring.electrical_subweights.voltage_margin,
            },
        },
        "cost_aware": (
            {
                "engineering_weight": config.cost_aware.engineering_weight,
                "lifecycle_cost_weight": config.cost_aware.lifecycle_cost_weight,
            }
            if config.cost_aware
            else None
        ),
        "costing": _costing_context(config),
    }
    serialized = json.dumps(
        state,
        allow_nan=False,
        separators=(",", ":"),
        sort_keys=True,
    )
    return hashlib.sha256(serialized.encode("utf-8")).hexdigest()


def _costing_context(config: OptimisationConfig) -> dict[str, Any] | None:
    if not config.costing:
        return None

    catalogue = config.costing.catalogue
    lifecycle = config.costing.lifecycle
    return {
        "catalogue": {
            "catalogue_id": catalogue.catalogue_id,
            "version": catalogue.version,
            "currency": catalogue.currency,
            "price_basis_date": catalogue.price_basis_date.isoformat(),
            "conductor_items": sorted(
                (
                    item.cable_type_id,
                    str(item.installed_cost_per_km_per_parallel_circuit),
                )
                for item in catalogue.conductor_items
            ),
            "pole_items": sorted(
                (item.pole_type, str(item.installed_cost_each))
                for item in catalogue.pole_items
            ),
            "land_policy": {
                "fixed_cost_per_affected_parcel": str(
                    catalogue.land_policy.fixed_cost_per_affected_parcel
                ),
                "variable_basis": catalogue.land_policy.variable_basis.value,
                "variable_rate": str(catalogue.land_policy.variable_rate),
            },
        },
        "lifecycle": {
            "currency": lifecycle.currency,
            "energy_price_basis_date": lifecycle.energy_price_basis_date.isoformat(),
            "analysis_period_years": lifecycle.analysis_period_years,
            "discount_rate": str(lifecycle.discount_rate),
            "annual_operating_hours": lifecycle.annual_operating_hours,
            "loss_load_factor": str(lifecycle.loss_load_factor),
            "energy_price_per_mwh": str(lifecycle.energy_price_per_mwh),
        },
    }
