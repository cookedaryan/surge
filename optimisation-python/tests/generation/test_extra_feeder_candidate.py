"""WP5-3 and WP5-4: the explicit ``k+1`` candidate and its synthetic evidence.

Golden-project ``k+1`` evidence is produced blinded in Stage 2 (S2-1); these
fixtures are synthetic only.
"""

from typing import Any

import pytest

import app.algorithms.wtg_grouping as grouping_module
import app.optimisation.scenarios as scenarios_module
from app.algorithms.physical_routing import RouteNotFoundError
from app.algorithms.route_graph import build_project_graph
from app.algorithms.solver_models import SolverOptions, SolverTelemetry
from app.algorithms.wtg_grouping import FeederGroupingResult, GroupingObjective
from app.contracts.codes import ExtraFeederOutcome, SolverStatus
from app.contracts.evidence import CandidateEvidence, CandidateFingerprints
from app.optimisation.scenario_models import (
    AttemptOutcome,
    GenerationSchedule,
    ScenarioGenerationConfig,
    ScenarioGenerationResult,
    ScenarioStrategy,
)
from app.optimisation.scenarios import (
    _build_scenario_parameters,
    _generate_extra_feeder_candidate,
    extra_feeder_outcome,
    generate_pnc_scenarios,
)
from app.pnc.models import ProjectPNCNetwork
from tests.test_scenarios import (
    _LARGE_SURFACE,
    _SMALL_SURFACE,
    _make_diverse_project,
    _make_project,
)

CAPACITY_MW = 30.0
V1 = GenerationSchedule.V1


def _generate(candidate_count: int = 3, **config: Any) -> ScenarioGenerationResult:
    return generate_pnc_scenarios(
        _make_diverse_project(),
        CAPACITY_MW,
        _LARGE_SURFACE,
        ScenarioGenerationConfig(
            candidate_count=candidate_count, generation_schedule=V1, **config
        ),
    )


def _extra_attempt(result: ScenarioGenerationResult) -> Any:
    (attempt,) = [a for a in result.attempts if a.parameter_set_id == "PS-006"]
    return attempt


def _capacity_valid(network: ProjectPNCNetwork, turbines: int) -> bool:
    return sum(network.wtg_count_by_feeder.values()) == turbines and all(
        count * 5.0 <= CAPACITY_MW for count in network.wtg_count_by_feeder.values()
    )


# --- success --------------------------------------------------------------------------


def test_v1_emits_a_capacity_valid_k_plus_one_candidate() -> None:
    result = _generate()
    baseline, extra, alternative = result.candidates
    assert [c.scenario_id for c in result.candidates] == [
        "SCN-001",
        "SCN-002",
        "SCN-003",
    ]
    assert baseline.strategy == ScenarioStrategy.BASELINE
    assert alternative.strategy == ScenarioStrategy.ALTERNATIVE_GROUPING

    assert extra.strategy == ScenarioStrategy.EXTRA_FEEDER
    assert extra.parameters.feeder_count_offset == 1
    assert extra.feeder_count == baseline.feeder_count + 1 == 3
    assert _capacity_valid(extra.network, 12)
    assert extra.topology_fingerprint != baseline.topology_fingerprint

    attempt = _extra_attempt(result)
    assert attempt.outcome == AttemptOutcome.ACCEPTED
    assert attempt.extra_feeder_outcome == ExtraFeederOutcome.ACCEPTED
    assert extra_feeder_outcome(result) == ExtraFeederOutcome.ACCEPTED
    assert 3 in [run.feeder_count for run in result.solver_runs]


def test_k_plus_one_generation_is_deterministic() -> None:
    first, second = _generate(), _generate()
    assert first.attempts == second.attempts
    assert [
        (c.scenario_id, c.topology_fingerprint, c.wtg_count_by_feeder)
        for c in first.candidates
    ] == [
        (c.scenario_id, c.topology_fingerprint, c.wtg_count_by_feeder)
        for c in second.candidates
    ]


def test_solver_options_reach_every_grouping_untouched(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    seen: list[tuple[int | None, SolverOptions | None]] = []
    original = scenarios_module.group_wtgs

    def capture(*args: Any, **kwargs: Any) -> FeederGroupingResult:
        seen.append((kwargs.get("feeder_count"), kwargs.get("solver_options")))
        return original(*args, **kwargs)

    monkeypatch.setattr(scenarios_module, "group_wtgs", capture)
    options = SolverOptions(time_limit_s=30.0)
    _generate(solver_options=options)
    assert (3, options) in seen
    assert all(value is options for _, value in seen)


def test_a_single_candidate_request_makes_no_k_plus_one_attempt() -> None:
    result = _generate(candidate_count=1)
    assert [a.parameter_set_id for a in result.attempts] == ["PS-001"]
    assert extra_feeder_outcome(result) == ExtraFeederOutcome.NOT_APPLICABLE


# --- failure evidence -----------------------------------------------------------------


def test_k_plus_one_is_infeasible_when_every_turbine_already_has_a_feeder() -> None:
    # Each 5 MW turbine fills a 5 MW feeder, so k equals the turbine count.
    project = _make_project(
        ("T1", 100.0, 100.0), ("T2", 200.0, 200.0), ("T3", 300.0, 100.0)
    )
    result = generate_pnc_scenarios(
        project,
        5.0,
        _SMALL_SURFACE,
        ScenarioGenerationConfig(candidate_count=3, generation_schedule=V1),
    )
    attempt = _extra_attempt(result)
    assert attempt.outcome == AttemptOutcome.GROUPING_FAILED
    assert attempt.extra_feeder_outcome == ExtraFeederOutcome.CAPACITY_INFEASIBLE
    assert "4 non-empty feeders" in attempt.detail
    assert all(c.strategy != ScenarioStrategy.EXTRA_FEEDER for c in result.candidates)
    assert all(run.feeder_count <= 3 for run in result.solver_runs)


def test_k_plus_one_that_would_collapse_onto_k_feeders_is_never_published(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # A solve that leaves the extra feeder empty would reproduce a k-feeder
    # design. It is reported as infeasible instead of duplicating k.
    original = grouping_module._solve_milp_assignment

    def leave_one_empty(coords: list[Any], *args: Any) -> Any:
        assignments, telemetry = original(coords, *args)
        k = args[2]
        if k == 3 and assignments is not None:
            # Spread the third feeder's turbines over the other two, within capacity.
            moved = iter([0, 1] * len(assignments))
            assignments = [next(moved) if a == 2 else a for a in assignments]
        return assignments, telemetry

    monkeypatch.setattr(grouping_module, "_solve_milp_assignment", leave_one_empty)
    result = _generate()
    attempt = _extra_attempt(result)
    assert attempt.extra_feeder_outcome == ExtraFeederOutcome.CAPACITY_INFEASIBLE
    assert "exactly 3 non-empty feeders" in attempt.detail
    assert "OPTIMAL" in attempt.detail
    assert all(c.feeder_count == 2 for c in result.candidates)


def test_k_plus_one_duplicating_an_accepted_topology_is_suppressed() -> None:
    accepted = _generate()
    extra = accepted.candidates[1]
    project = _make_diverse_project()
    (parameters,) = [
        p
        for p in _build_scenario_parameters(CAPACITY_MW, 5, V1)
        if p.feeder_count_offset
    ]
    graph = build_project_graph(project)
    substation = next(
        n for n, d in graph.nodes(data=True) if d.get("type") == "substation"
    )
    network, fingerprint, outcome, _, extra_outcome = _generate_extra_feeder_candidate(
        project=project,
        feeder_capacity_mw=CAPACITY_MW,
        cost_surface=_LARGE_SURFACE,
        project_id="PROJECT",
        parameters=parameters,
        base_graph=graph,
        substation_node=substation,
        accepted_fingerprints={extra.topology_fingerprint},
        solver_options=None,
        solver_runs=[],
        minimum_feeder_counts={(42, GroupingObjective.MINIMIZE_DISTANCE): 2},
    )
    assert network is None
    assert fingerprint == extra.topology_fingerprint
    assert outcome == AttemptOutcome.DUPLICATE_TOPOLOGY
    assert extra_outcome == ExtraFeederOutcome.DUPLICATE_TOPOLOGY


def test_a_solver_limit_is_not_reported_as_infeasible(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    original = scenarios_module.group_wtgs

    def limited(*args: Any, **kwargs: Any) -> FeederGroupingResult:
        if kwargs.get("feeder_count") is None:
            return original(*args, **kwargs)
        run = SolverTelemetry(
            objective="minimize_distance",
            feeder_count=kwargs["feeder_count"],
            status=SolverStatus.LIMIT_REACHED,
            wall_time_s=30.0,
            mip_gap=None,
            time_limit_s=30.0,
            node_limit=None,
            limit_reached=True,
        )
        return FeederGroupingResult(feeder_count=0, assignments=(), solver_runs=(run,))

    monkeypatch.setattr(scenarios_module, "group_wtgs", limited)
    attempt = _extra_attempt(_generate())
    assert attempt.extra_feeder_outcome == ExtraFeederOutcome.SOLVER_LIMIT_REACHED
    assert "LIMIT_REACHED" in attempt.detail


def test_routing_failure_of_the_k_plus_one_candidate_is_evaluation_failed(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    original = scenarios_module.route_collector_topology

    def fail_for_three_feeders(topology: Any, *args: Any) -> Any:
        if len(topology.feeders) == 3:
            raise RouteNotFoundError("F3", "substation", "wtg", "synthetic")
        return original(topology, *args)

    monkeypatch.setattr(
        scenarios_module, "route_collector_topology", fail_for_three_feeders
    )
    attempt = _extra_attempt(_generate())
    assert attempt.outcome == AttemptOutcome.ROUTING_FAILED
    assert attempt.extra_feeder_outcome == ExtraFeederOutcome.EVALUATION_FAILED


def test_k_plus_one_without_a_baseline_minimum_is_not_applicable() -> None:
    project = _make_diverse_project()
    (parameters,) = [
        p
        for p in _build_scenario_parameters(CAPACITY_MW, 5, V1)
        if p.feeder_count_offset
    ]
    *_, extra_outcome = _generate_extra_feeder_candidate(
        project=project,
        feeder_capacity_mw=CAPACITY_MW,
        cost_surface=_LARGE_SURFACE,
        project_id="PROJECT",
        parameters=parameters,
        base_graph=build_project_graph(project),
        substation_node="substation",
        accepted_fingerprints=set(),
        solver_options=None,
        solver_runs=[],
        minimum_feeder_counts={},
    )
    assert extra_outcome == ExtraFeederOutcome.NOT_APPLICABLE


# --- C4 evidence shape ----------------------------------------------------------------


def test_outcomes_fit_the_c4_candidate_evidence_field() -> None:
    result = _generate()
    extra = result.candidates[1]
    evidence = CandidateEvidence(
        candidate_id=extra.scenario_id,
        parent_id=None,
        mutation_type=None,
        fingerprints=CandidateFingerprints(
            topology=None, geometry=None, final_design=None, canonicaliser_versions={}
        ),
        feasible=True,
        eligible=True,
        failure_codes=[],
        raw_metrics={},
        contributions=None,
        extra_feeder_outcome=extra_feeder_outcome(result),
    )
    assert evidence.model_dump(mode="json")["extra_feeder_outcome"] == "ACCEPTED"
