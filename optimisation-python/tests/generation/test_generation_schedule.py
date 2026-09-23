"""WP5-2: the V1 schedule sits behind the C5 flags; V0 stays as it was (C12)."""

from dataclasses import replace
from typing import Any

import pytest
from fastapi.testclient import TestClient

import app.api.v1.endpoints.optimise as optimise_endpoint
from app.contracts.codes import ContractErrorCode, ExtraFeederOutcome
from app.contracts.errors import ContractError
from app.contracts.resolution import V0_PROFILE_RESOLUTION
from app.core.config import Settings
from app.main import app
from app.optimisation.profiles.resolve import resolve_profile
from app.optimisation.scenario_models import (
    PARAMETER_SCHEDULE,
    V1_PARAMETER_SCHEDULE,
    GenerationSchedule,
    InvalidScenarioConfigError,
    ScenarioGenerationConfig,
    ScenarioStrategy,
)
from app.optimisation.scenarios import (
    _apply_long_edge_penalty,
    _build_scenario_parameters,
    extra_feeder_outcome,
    generate_pnc_scenarios,
)
from app.optimisation.workflow_models import OptimisationConfig
from app.schemas.optimise import OptimisationRequest
from tests.test_optimise import create_payload
from tests.test_scenarios import _LARGE_SURFACE, _make_diverse_project

# --- schedules ------------------------------------------------------------------------


def test_v0_is_the_default_and_materialises_the_unchanged_schedule() -> None:
    assert ScenarioGenerationConfig().generation_schedule == GenerationSchedule.V0
    params = _build_scenario_parameters(30.0, 5)
    assert params == _build_scenario_parameters(30.0, 5, GenerationSchedule.V0)
    assert [
        (
            p.parameter_set_id,
            p.strategy,
            p.grouping_seed,
            p.grouping_objective,
            p.topology_weight_profile,
            p.topology_penalty,
        )
        for p in params
    ] == list(PARAMETER_SCHEDULE)
    assert all(p.feeder_count_offset == 0 for p in params)


def test_v1_gates_out_the_ineffective_personalities_and_adds_k_plus_one() -> None:
    params = _build_scenario_parameters(30.0, 5, GenerationSchedule.V1)
    assert [p.parameter_set_id for p in params] == [
        "PS-001",
        "PS-006",
        "PS-002",
        "PS-003",
    ]
    strategies = {p.strategy for p in params}
    assert ScenarioStrategy.LONG_EDGE_PENALTY not in strategies
    assert ScenarioStrategy.ALTERNATIVE_GROUPING_BALANCED not in strategies
    assert [p.feeder_count_offset for p in params] == [0, 1, 0, 0]

    baseline, extra = params[0], params[1]
    assert extra.strategy == ScenarioStrategy.EXTRA_FEEDER
    # k comes from the baseline entry, so it must run first with the same inputs.
    assert (extra.grouping_seed, extra.grouping_objective) == (
        baseline.grouping_seed,
        baseline.grouping_objective,
    )
    assert V1_PARAMETER_SCHEDULE[0][0] == PARAMETER_SCHEDULE[0]


def test_the_long_edge_transform_is_gated_not_deleted() -> None:
    import networkx as nx

    graph = nx.Graph()
    graph.add_edge("a", "b", weight=1.0)
    graph.add_edge("b", "c", weight=2.0)
    penalised = _apply_long_edge_penalty(graph, 2.0)
    assert penalised["b"]["c"]["weight"] == pytest.approx(6.0)
    assert graph["b"]["c"]["weight"] == 2.0


def test_schedule_must_be_a_generation_schedule() -> None:
    with pytest.raises(InvalidScenarioConfigError):
        ScenarioGenerationConfig(generation_schedule="v1")  # type: ignore[arg-type]


def test_v0_generation_makes_no_extra_feeder_attempt() -> None:
    project = _make_diverse_project()
    default = generate_pnc_scenarios(project, 30.0, _LARGE_SURFACE)
    explicit = generate_pnc_scenarios(
        project,
        30.0,
        _LARGE_SURFACE,
        ScenarioGenerationConfig(generation_schedule=GenerationSchedule.V0),
    )
    # Networks hold graphs without value equality, so compare IDs and fingerprints.
    assert explicit.attempts == default.attempts
    assert [(c.scenario_id, c.topology_fingerprint) for c in explicit.candidates] == [
        (c.scenario_id, c.topology_fingerprint) for c in default.candidates
    ]
    assert [a.parameter_set_id for a in default.attempts] == [
        "PS-001",
        "PS-002",
        "PS-003",
    ]
    assert all(a.extra_feeder_outcome is None for a in default.attempts)
    assert all(c.strategy != ScenarioStrategy.EXTRA_FEEDER for c in default.candidates)
    assert extra_feeder_outcome(default) == ExtraFeederOutcome.NOT_APPLICABLE


# --- C5 gate in the request path ------------------------------------------------------


def _request(**overrides: Any) -> OptimisationRequest:
    return OptimisationRequest.model_validate({**create_payload(), **overrides})


def test_both_flags_off_resolves_exactly_to_v0() -> None:
    assert resolve_profile(_request(), Settings()) is V0_PROFILE_RESOLUTION


@pytest.mark.parametrize(
    "settings",
    [Settings(surge_profiles_enabled=True), Settings(surge_search_enabled=True)],
    ids=["profiles-flag", "search-flag"],
)
def test_either_flag_selects_the_v1_schedule_and_nothing_else(
    settings: Settings,
) -> None:
    resolution = resolve_profile(_request(), settings)
    assert (resolution.profile_id, resolution.profile_version) == (None, None)

    config = _workflow_config()
    configured = resolution.configure(config)
    assert configured.scenario.generation_schedule == GenerationSchedule.V1
    assert configured == replace(
        config,
        scenario=replace(config.scenario, generation_schedule=GenerationSchedule.V1),
    )


def test_an_explicit_profile_is_refused_while_the_profiles_flag_is_off() -> None:
    settings = Settings(surge_profiles_enabled=False, surge_search_enabled=True)
    with pytest.raises(ContractError) as raised:
        resolve_profile(_request(profile={"id": "balanced", "version": "1"}), settings)
    assert raised.value.code == ContractErrorCode.PROFILE_NOT_SUPPORTED


def test_an_explicit_profile_resolves_and_still_selects_the_v1_schedule() -> None:
    # WP5-2 asserted a refusal here, which was true while nothing consumed a
    # resolved profile. Now selection drives the recommendation, so the profile
    # resolves - and it must still switch the generation schedule, because the C5
    # gate is what the profiles flag turns on.
    settings = Settings(surge_profiles_enabled=True, surge_search_enabled=True)

    resolution = resolve_profile(
        _request(profile={"id": "balanced", "version": "1"}), settings
    )

    assert resolution.profile_id == "balanced"
    assert resolution.profile_version == "1"
    config = _workflow_config()
    configured = resolution.configure(config)
    assert configured.scenario.generation_schedule == GenerationSchedule.V1
    assert configured.scoring.profile is not None
    assert configured.scoring.profile.profile_id.value == "balanced"


def _workflow_config() -> OptimisationConfig:
    from app.schemas.legacy_mapping import legacy_to_workflow_invocation

    return legacy_to_workflow_invocation(_request()).config


@pytest.mark.parametrize(
    ("settings", "expected"),
    [
        (Settings(), GenerationSchedule.V0),
        (Settings(surge_search_enabled=True), GenerationSchedule.V1),
        (Settings(surge_profiles_enabled=True), GenerationSchedule.V1),
    ],
)
def test_endpoint_runs_the_schedule_the_flags_select(
    monkeypatch: pytest.MonkeyPatch,
    settings: Settings,
    expected: GenerationSchedule,
) -> None:
    captured: list[OptimisationConfig] = []

    def capture(project_input: object, config: OptimisationConfig, **_: Any) -> None:
        captured.append(config)
        raise ValueError("stop after capture")

    monkeypatch.setattr(optimise_endpoint, "get_settings", lambda: settings)
    monkeypatch.setattr(optimise_endpoint, "optimise_project", capture)
    response = TestClient(app).post("/api/v1/optimise", json=create_payload())
    assert response.status_code == 422
    (config,) = captured
    assert config.scenario.generation_schedule == expected
