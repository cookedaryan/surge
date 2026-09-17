"""Stage 0 seams (CON-2): each is present and changes no V0 behaviour."""

from dataclasses import replace

import pytest
from fastapi.testclient import TestClient
from pyproj import CRS
from shapely.geometry import Point

import app.api.v1.endpoints.optimise as optimise_endpoint
import tests.test_optimisation_orchestrator as orchestrator_fixtures
from app.algorithms.solver_models import SolverOptions
from app.algorithms.wtg_grouping import GroupingObjective, group_wtgs
from app.contracts.codes import ContractErrorCode, GuardPoint, SolverStatus
from app.core.config import Settings
from app.gis.constraints import parse_constraint_layers
from app.main import app
from app.models.spatial import ProjectSpatialData, Substation, WindTurbine
from app.optimisation.orchestrator import optimise_project
from app.optimisation.run_guard import (
    NULL_RUN_GUARD,
    CompositeRunGuard,
    RunCancelledError,
    RunGuardContext,
    build_run_guard,
)
from app.optimisation.search_models import CandidateSearchConfig
from scripts.contracts.export_contracts import CONTRACTS
from tests.test_optimise import create_payload

client = TestClient(app)

_UTM_44N = CRS.from_epsg(32644)


def _two_feeder_project() -> ProjectSpatialData:
    turbines = tuple(
        WindTurbine(
            turbine_id=f"T{index}",
            location=Point(500000 + index * 900.0, 800000 + (index % 2) * 400.0),
            capacity_mw=6.0,
        )
        for index in range(4)
    )
    return ProjectSpatialData(
        turbines=turbines,
        substation=Substation(substation_id="SS", location=Point(499000, 800000)),
        projected_crs=_UTM_44N,
    )


class RecordingGuard:
    def __init__(self, stop_at: GuardPoint | None = None) -> None:
        self.points: list[GuardPoint] = []
        self.stop_at = stop_at

    def check(self, point: GuardPoint) -> None:
        self.points.append(point)
        if point == self.stop_at:
            raise RunCancelledError(point)


# --- S5 solver seam ---------------------------------------------------------


@pytest.mark.parametrize(
    "objective",
    [GroupingObjective.MINIMIZE_DISTANCE, GroupingObjective.BALANCE_WTG_COUNT],
)
def test_grouping_records_solver_telemetry_without_changing_the_result(
    objective: GroupingObjective,
) -> None:
    project = _two_feeder_project()
    plain = group_wtgs(project, 12.0, objective=objective)
    limited = group_wtgs(
        project,
        12.0,
        objective=objective,
        solver_options=SolverOptions(time_limit_s=30.0, node_limit=1000),
    )
    assert plain == limited
    assert plain.solver_runs
    final = plain.solver_runs[-1]
    assert final.status == SolverStatus.OPTIMAL
    assert final.feeder_count == plain.feeder_count
    assert final.objective == objective.value
    assert final.wall_time_s >= 0
    assert not final.limit_reached
    # Stage 0 threads the options but applies none.
    assert final.time_limit_s is None and final.node_limit is None


def test_feeder_count_override_is_reserved_for_wp5() -> None:
    with pytest.raises(NotImplementedError):
        group_wtgs(_two_feeder_project(), 12.0, feeder_count=3)


@pytest.mark.parametrize(
    "options",
    [{"time_limit_s": 0.0}, {"time_limit_s": float("inf")}, {"node_limit": 0}],
)
def test_solver_options_reject_invalid_limits(options: dict[str, float]) -> None:
    with pytest.raises(ValueError):
        SolverOptions(**options)  # type: ignore[arg-type]


# --- S4 run guard -------------------------------------------------------------


def test_default_run_guard_never_stops() -> None:
    guard = build_run_guard(RunGuardContext(run_id="job-1"))
    assert isinstance(guard, CompositeRunGuard)
    for point in GuardPoint:
        guard.check(point)
        NULL_RUN_GUARD.check(point)


def test_orchestrator_consults_the_guard_before_seed_work() -> None:
    guard = RecordingGuard()
    result = optimise_project(
        orchestrator_fixtures.project_input.__wrapped__(),
        orchestrator_fixtures.base_config.__wrapped__(),
        run_guard=guard,
    )
    assert result.status.value in {"SUCCESS", "PARTIAL_SUCCESS"}
    assert guard.points[0] == GuardPoint.BEFORE_SEED_GENERATION
    assert guard.points.count(GuardPoint.BEFORE_SEED_EVALUATION) == len(
        result.generation_result.candidates  # type: ignore[union-attr]
    )
    assert result.generation_result is not None
    assert result.generation_result.solver_runs


def test_search_consults_the_guard_before_child_routing() -> None:
    guard = RecordingGuard()
    config = replace(
        orchestrator_fixtures.base_config.__wrapped__(),
        search=CandidateSearchConfig(
            enabled=True, max_rounds=1, beam_width=1, max_neighbors_per_parent=2
        ),
    )
    optimise_project(
        orchestrator_fixtures.project_input.__wrapped__(), config, run_guard=guard
    )
    assert GuardPoint.BEFORE_CHILD_ROUTING in guard.points


def test_cancellation_propagates_instead_of_becoming_a_workflow_failure() -> None:
    config = replace(
        orchestrator_fixtures.base_config.__wrapped__(),
        search=CandidateSearchConfig(
            enabled=True, max_rounds=1, beam_width=1, max_neighbors_per_parent=2
        ),
    )
    with pytest.raises(RunCancelledError):
        optimise_project(
            orchestrator_fixtures.project_input.__wrapped__(),
            config,
            run_guard=RecordingGuard(stop_at=GuardPoint.BEFORE_CHILD_ROUTING),
        )


# --- S2 / S7 endpoint seams ---------------------------------------------------


def test_explicit_profile_is_refused_with_a_stable_code() -> None:
    payload = create_payload()
    payload["profile"] = {"id": "balanced", "version": "1"}
    response = client.post("/api/v1/optimise", json=payload)
    assert response.status_code == 422
    assert response.json()["detail"]["code"] == (
        ContractErrorCode.PROFILE_NOT_SUPPORTED.value
    )


def test_v0_request_has_no_additive_blocks() -> None:
    response = client.post(
        "/api/v1/optimise",
        json=create_payload(),
        headers={"X-Surge-Run-Id": "job-seam-test"},
    )
    assert response.status_code == 200
    rules = (CONTRACTS / "response-rules.json").read_text(encoding="utf-8")
    for block in ("design_truth", "search_evidence", "solver_runs"):
        assert block in rules
        assert block not in response.json()


def test_cancelled_run_answers_409(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        optimise_endpoint,
        "build_run_guard",
        lambda context: RecordingGuard(stop_at=GuardPoint.BEFORE_SEED_GENERATION),
    )
    response = client.post("/api/v1/optimise", json=create_payload())
    assert response.status_code == 409
    assert response.json()["detail"]["code"] == "CANCELLED"


@pytest.mark.parametrize(
    ("method", "path"),
    [
        ("post", "/api/v1/runs/job-1/cancel"),
        ("get", "/api/v1/profiles/definition-hash"),
    ],
)
def test_reserved_routes_answer_not_implemented(method: str, path: str) -> None:
    response = getattr(client, method)(path)
    assert response.status_code == 501
    assert response.json()["detail"]["code"] == "NOT_IMPLEMENTED"


# --- S1 typed identity and C5 flags -------------------------------------------


def _feature(properties: dict[str, object]) -> dict[str, object]:
    return {
        "type": "Feature",
        "properties": properties,
        "geometry": {
            "type": "Polygon",
            "coordinates": [
                [[77.2, 14.38], [77.21, 14.38], [77.21, 14.39], [77.2, 14.38]]
            ],
        },
    }


def test_typed_identity_is_carried_through_unvalidated() -> None:
    layers = parse_constraint_layers(
        {
            "type": "FeatureCollection",
            "features": [
                _feature(
                    {
                        "constraint_id": "a",
                        "constraint_type": "restricted_area",
                        "routing_mode": "hard",
                        "source_id": "src-1",
                        "feature_type": "forest",
                    }
                ),
                _feature(
                    {
                        "constraint_id": "b",
                        "constraint_type": "restricted_area",
                        "routing_mode": "hard",
                    }
                ),
            ],
        },
        target_crs=_UTM_44N,
        default_buffer_m=10.0,
        default_soft_cost_weight=20.0,
    )
    typed, plain = layers
    assert (typed.source_id, typed.feature_type) == ("src-1", "forest")
    assert (plain.source_id, plain.feature_type) == (None, None)
    assert typed.layer_type == plain.layer_type


def test_flags_default_off_and_gate_the_new_schedule() -> None:
    settings = Settings()
    assert not settings.surge_profiles_enabled
    assert not settings.surge_search_enabled
    assert not settings.new_generation_schedule_enabled
    assert Settings(surge_search_enabled=True).new_generation_schedule_enabled


# --- WP0A-3 feeder/segment identity (Python side of C11) ----------------------


def test_v1_route_features_carry_one_segment_under_one_feeder() -> None:
    response = client.post("/api/v1/optimise", json=create_payload())
    features = response.json()["feeder_routes_geojson"]["features"]
    assert features
    segment_ids = [feature["properties"]["segment_id"] for feature in features]
    assert len(segment_ids) == len(set(segment_ids))
    for feature in features:
        properties = feature["properties"]
        assert properties["feature_type"] == "pnc_segment"
        assert properties["feederName"] == properties["feeder_id"]
