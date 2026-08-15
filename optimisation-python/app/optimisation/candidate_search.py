from collections.abc import Mapping
from dataclasses import replace
from heapq import nsmallest
from itertools import chain
from math import inf

import networkx as nx
from shapely.geometry import Point

from app.algorithms.topology import (
    CollectorTopologyResult,
    FeederTopology,
    build_feeder_mst,
)
from app.algorithms.wtg_grouping import FeederAssignment, FeederGroupingResult
from app.gis.cost_surface import CostSurface
from app.models.spatial import WindTurbine
from app.optimisation.candidate_evaluation import evaluate_candidate
from app.optimisation.scenario_builder import materialize_candidate_design
from app.optimisation.scenario_models import (
    AttemptOutcome,
    PNCScenario,
    ScenarioStrategy,
)
from app.optimisation.scenarios import design_fingerprint
from app.optimisation.scoring import evaluate_cohort
from app.optimisation.scoring_models import (
    ElectricallyEvaluatedScenario,
    EngineeringEvaluatedScenario,
    OptimizationRecommendation,
)
from app.optimisation.search_models import (
    CandidateLineage,
    CandidateSearchResult,
    EdgeReconnectMutation,
    FeederReassignmentMutation,
    FeederSwapMutation,
)
from app.optimisation.workflow_models import (
    CandidateWorkflowResult,
    OptimisationConfig,
    ProjectInput,
    WorkflowFailureCode,
)


def _raw_wtg_id(node_id: str) -> str | None:
    if node_id.startswith("wtg:"):
        return node_id[4:]
    return None


def _get_turbine(turbines_by_id: Mapping[str, WindTurbine], wtg_id: str) -> WindTurbine:
    try:
        return turbines_by_id[wtg_id]
    except KeyError as exc:
        raise ValueError(f"Turbine {wtg_id} not found in project.") from exc


def _recompute_feeder_assignment(
    feeder_id: str,
    wtg_ids: set[str],
    turbines_by_id: Mapping[str, WindTurbine],
) -> FeederAssignment:
    total_mw = 0.0
    sum_x = 0.0
    sum_y = 0.0
    count = len(wtg_ids)
    if count == 0:
        return FeederAssignment(feeder_id, (), 0.0, Point(0, 0))

    sorted_ids = tuple(sorted(wtg_ids))
    for wtg_id in sorted_ids:
        turbine = _get_turbine(turbines_by_id, wtg_id)
        total_mw += turbine.capacity_mw or 0.0
        loc = turbine.location
        sum_x += loc.x
        sum_y += loc.y

    return FeederAssignment(
        feeder_id=feeder_id,
        turbine_ids=sorted_ids,
        total_capacity_mw=total_mw,
        centroid=Point(sum_x / count, sum_y / count),
    )


def _generate_reassignment_mutations(
    base_graph: nx.Graph,
    grouping: FeederGroupingResult,
    turbines_by_id: Mapping[str, WindTurbine],
    feeder_capacity_mw: float,
) -> list[tuple[float, FeederReassignmentMutation]]:
    wtg_to_feeder = {}
    feeder_capacities = {}
    for assignment in grouping.assignments:
        feeder_capacities[assignment.feeder_id] = assignment.total_capacity_mw
        for t_id in assignment.turbine_ids:
            wtg_to_feeder[t_id] = assignment.feeder_id

    mutations = []
    seen = set()

    for u, v, data in base_graph.edges(data=True):
        u_raw = _raw_wtg_id(u)
        v_raw = _raw_wtg_id(v)
        if not u_raw or not v_raw:
            continue

        f_u = wtg_to_feeder.get(u_raw)
        f_v = wtg_to_feeder.get(v_raw)
        if not f_u or not f_v or f_u == f_v:
            continue

        weight = data.get("weight", 0.0)

        # Consider moving u to f_v
        u_cap = _get_turbine(turbines_by_id, u_raw).capacity_mw or 0.0
        if feeder_capacities[f_v] + u_cap <= feeder_capacity_mw:
            mut = FeederReassignmentMutation(u_raw, f_u, f_v)
            mut_tuple = (mut.wtg_id, mut.target_feeder_id)
            if mut_tuple not in seen:
                seen.add(mut_tuple)
                mutations.append((weight, mut))

        # Consider moving v to f_u
        v_cap = _get_turbine(turbines_by_id, v_raw).capacity_mw or 0.0
        if feeder_capacities[f_u] + v_cap <= feeder_capacity_mw:
            mut = FeederReassignmentMutation(v_raw, f_v, f_u)
            mut_tuple = (mut.wtg_id, mut.target_feeder_id)
            if mut_tuple not in seen:
                seen.add(mut_tuple)
                mutations.append((weight, mut))

    return mutations


def _generate_swap_mutations(
    base_graph: nx.Graph,
    grouping: FeederGroupingResult,
    turbines_by_id: Mapping[str, WindTurbine],
    feeder_capacity_mw: float,
) -> list[tuple[float, FeederSwapMutation]]:
    wtg_to_feeder = {}
    feeder_capacities = {}
    for assignment in grouping.assignments:
        feeder_capacities[assignment.feeder_id] = assignment.total_capacity_mw
        for t_id in assignment.turbine_ids:
            wtg_to_feeder[t_id] = assignment.feeder_id

    mutations = []
    seen = set()

    for u, v, data in base_graph.edges(data=True):
        u_raw = _raw_wtg_id(u)
        v_raw = _raw_wtg_id(v)
        if not u_raw or not v_raw:
            continue

        f_u = wtg_to_feeder.get(u_raw)
        f_v = wtg_to_feeder.get(v_raw)
        if not f_u or not f_v or f_u == f_v:
            continue

        u_cap = _get_turbine(turbines_by_id, u_raw).capacity_mw or 0.0
        v_cap = _get_turbine(turbines_by_id, v_raw).capacity_mw or 0.0

        if (feeder_capacities[f_u] + v_cap - u_cap <= feeder_capacity_mw) and (
            feeder_capacities[f_v] + u_cap - v_cap <= feeder_capacity_mw
        ):
            w1, w2 = u_raw, v_raw
            f1, f2 = f_u, f_v
            if w1 > w2:
                w1, w2 = w2, w1
                f1, f2 = f2, f1

            mut = FeederSwapMutation(w1, f1, w2, f2)
            weight = data.get("weight", 0.0)
            mut_tuple = (mut.wtg_id_1, mut.wtg_id_2)
            if mut_tuple not in seen:
                seen.add(mut_tuple)
                mutations.append((weight, mut))

    return mutations


def _generate_reconnect_mutations(
    base_graph: nx.Graph,
    topology: CollectorTopologyResult,
) -> list[tuple[float, EdgeReconnectMutation]]:
    mutations = []

    for feeder in topology.feeders:
        for u, v in feeder.mst_edges:
            mst = feeder.mst_graph.copy()
            mst.remove_edge(u, v)

            components = list(nx.connected_components(mst))
            if len(components) != 2:
                continue

            comp1, comp2 = components

            best_edge = None
            best_weight = float("inf")
            original_weight = (
                base_graph[u][v].get("weight", 0.0)
                if base_graph.has_edge(u, v)
                else 0.0
            )

            for n1 in comp1:
                for n2 in comp2:
                    if base_graph.has_edge(n1, n2):
                        w = base_graph[n1][n2].get("weight", float("inf"))
                        if (n1 == u and n2 == v) or (n1 == v and n2 == u):
                            continue
                        if w < best_weight:
                            best_weight = w
                            best_edge = (min(n1, n2), max(n1, n2))

            if best_edge:
                mut = EdgeReconnectMutation(
                    feeder.feeder_id, (min(u, v), max(u, v)), best_edge
                )
                delta = best_weight - original_weight
                mutations.append((delta, mut))

    return mutations


def _apply_grouping_mutation(
    grouping: FeederGroupingResult,
    turbines_by_id: Mapping[str, WindTurbine],
    mutation: FeederReassignmentMutation | FeederSwapMutation,
) -> FeederGroupingResult:
    feeder_wtgs = {a.feeder_id: set(a.turbine_ids) for a in grouping.assignments}

    if isinstance(mutation, FeederReassignmentMutation):
        feeder_wtgs[mutation.source_feeder_id].remove(mutation.wtg_id)
        feeder_wtgs[mutation.target_feeder_id].add(mutation.wtg_id)
    elif isinstance(mutation, FeederSwapMutation):
        feeder_wtgs[mutation.feeder_id_1].remove(mutation.wtg_id_1)
        feeder_wtgs[mutation.feeder_id_2].add(mutation.wtg_id_1)

        feeder_wtgs[mutation.feeder_id_2].remove(mutation.wtg_id_2)
        feeder_wtgs[mutation.feeder_id_1].add(mutation.wtg_id_2)

    new_assignments = []
    for fid, wtgs in feeder_wtgs.items():
        if wtgs:
            new_assignments.append(
                _recompute_feeder_assignment(fid, wtgs, turbines_by_id)
            )

    new_assignments.sort(key=lambda x: (x.centroid.x, x.centroid.y, x.feeder_id))
    return FeederGroupingResult(len(new_assignments), tuple(new_assignments))


def _apply_topology_mutation(
    topology: CollectorTopologyResult,
    base_graph: nx.Graph,
    mutation: EdgeReconnectMutation,
) -> CollectorTopologyResult:
    new_feeders = []
    for f in topology.feeders:
        if f.feeder_id != mutation.feeder_id:
            new_feeders.append(f)
            continue

        mst = f.mst_graph.copy()
        u, v = mutation.removed_edge
        mst.remove_edge(u, v)

        x, y = mutation.added_edge
        w = base_graph[x][y].get("weight", 0.0) if base_graph.has_edge(x, y) else 0.0
        mst.add_edge(x, y, weight=w)

        mst_edges = []
        total_length = 0.0
        for n1, n2, data in mst.edges(data=True):
            mst_edges.append((min(n1, n2), max(n1, n2)))
            total_length += data.get("weight", 0.0)

        new_feeders.append(
            FeederTopology(
                feeder_id=f.feeder_id,
                node_ids=tuple(mst.nodes()),
                total_capacity_mw=f.total_capacity_mw,
                total_length_m=total_length,
                mst_edges=tuple(sorted(mst_edges)),
                mst_graph=mst,
            )
        )

    return CollectorTopologyResult(tuple(new_feeders))


def _extract_design(
    scenario: PNCScenario,
    turbines_by_id: Mapping[str, WindTurbine],
    base_graph: nx.Graph,
) -> tuple[FeederGroupingResult, CollectorTopologyResult]:
    assignments = []
    feeder_topologies = []

    for feeder in scenario.network.feeders:
        wtg_ids = {
            wtg_id
            for node_id in feeder.wtg_ids
            if (wtg_id := _raw_wtg_id(node_id)) is not None
        }
        mst = nx.Graph()
        mst.add_nodes_from(feeder.mst_graph.nodes)
        for u, v in feeder.mst_graph.edges:
            w = (
                base_graph[u][v].get("weight", 0.0)
                if base_graph.has_edge(u, v)
                else 0.0
            )
            mst.add_edge(u, v, weight=w)

        assignments.append(
            _recompute_feeder_assignment(feeder.feeder_id, wtg_ids, turbines_by_id)
        )

        length = sum(data.get("weight", 0.0) for _, _, data in mst.edges(data=True))
        mst_edges = tuple(sorted((min(u, v), max(u, v)) for u, v in mst.edges))

        feeder_topologies.append(
            FeederTopology(
                feeder_id=feeder.feeder_id,
                node_ids=tuple(sorted(mst.nodes)),
                total_capacity_mw=assignments[-1].total_capacity_mw,
                total_length_m=length,
                mst_edges=mst_edges,
                mst_graph=mst,
            )
        )

    return (
        FeederGroupingResult(len(assignments), tuple(assignments)),
        CollectorTopologyResult(tuple(feeder_topologies)),
    )


def _score_archive(
    archive: dict[str, CandidateWorkflowResult],
    config: OptimisationConfig,
    electrical_context_id: str,
) -> tuple[dict[str, CandidateWorkflowResult], OptimizationRecommendation | None]:
    """Re-scores the entire eligible archive and updates their evaluation results."""
    eligible_candidates = [
        c
        for c in archive.values()
        if c.engineering_assessment is not None and c.load_flow_result is not None
    ]
    if not eligible_candidates:
        return archive, None

    wrappers = []
    for candidate in eligible_candidates:
        assert candidate.load_flow_result is not None
        assert candidate.engineering_assessment is not None
        wrappers.append(
            EngineeringEvaluatedScenario(
                electrical=ElectricallyEvaluatedScenario(
                    scenario=candidate.scenario,
                    load_flow_result=candidate.load_flow_result,
                    electrical_context_id=electrical_context_id,
                    cable_sizing=candidate.cable_sizing,
                    repair_log=candidate.repair_log,
                ),
                engineering_assessment=candidate.engineering_assessment,
                cost_assessment=candidate.cost_assessment,
            )
        )

    recommendation = evaluate_cohort(
        wrappers=tuple(wrappers),
        scoring_config=config.scoring,
        cost_aware_config=config.cost_aware,
    )

    scored_archive = dict(archive)
    if recommendation:
        eval_map = {e.assessment.scenario_id: e for e in recommendation.evaluations}
    else:
        eval_map = {}
    for c in eligible_candidates:
        if c.scenario.scenario_id in eval_map:
            updated_c = replace(c, evaluation=eval_map[c.scenario.scenario_id])
            scored_archive[c.scenario.scenario_id] = updated_c

    return scored_archive, recommendation


def run_candidate_beam_search(
    seeds: tuple[CandidateWorkflowResult, ...],
    project_input: ProjectInput,
    config: OptimisationConfig,
    base_graph: nx.Graph,
    cost_surface: CostSurface,
    substation_node_id: str,
    electrical_context_id: str,
) -> tuple[
    tuple[CandidateWorkflowResult, ...],
    OptimizationRecommendation | None,
    CandidateSearchResult,
]:
    """Runs deterministic beam search to improve network candidates."""
    search_config = config.search
    archive = {seed.scenario.scenario_id: seed for seed in seeds}
    if not search_config.enabled:
        scored_archive, recommendation = _score_archive(
            archive, config, electrical_context_id
        )
        return (
            tuple(scored_archive.values()),
            recommendation,
            CandidateSearchResult(
                rounds_completed=0,
                designs_generated=0,
                duplicate_designs_skipped=0,
                candidates_evaluated=0,
                candidates_failed=0,
                initial_best_scenario_id=None,
                final_best_scenario_id=None,
                initial_route_length_m=None,
                final_route_length_m=None,
                initial_lifecycle_cost=None,
                final_lifecycle_cost=None,
            ),
        )

    designs_generated = 0
    duplicate_designs_skipped = 0
    candidates_evaluated = 0
    candidates_failed = 0

    archive, current_rec = _score_archive(archive, config, electrical_context_id)

    def get_rank(candidate: CandidateWorkflowResult) -> float:
        evaluation = candidate.evaluation
        if (
            evaluation
            and evaluation.assessment.eligible
            and evaluation.rank is not None
        ):
            return float(evaluation.rank)
        return inf

    initial_best_scenario_id = None
    initial_route_length = None
    initial_lifecycle_cost = None

    if current_rec and current_rec.recommended_scenario_id:
        initial_best_scenario_id = current_rec.recommended_scenario_id
        winner = archive[initial_best_scenario_id]
        initial_route_length = winner.scenario.total_route_length_m
        if winner.cost_assessment and winner.cost_assessment.cost:
            initial_lifecycle_cost = float(winner.cost_assessment.cost.lifecycle_cost)

    evaluated_fingerprints = {s.scenario.topology_fingerprint for s in seeds}
    turbines_by_id = {
        turbine.turbine_id: turbine for turbine in project_input.project_data.turbines
    }

    frontier_pool = []
    for s in seeds:
        grouping, topology = _extract_design(s.scenario, turbines_by_id, base_graph)
        rank = get_rank(archive[s.scenario.scenario_id])
        if rank != inf:
            frontier_pool.append((rank, s.scenario.scenario_id, grouping, topology))

    frontier_pool.sort(key=lambda x: x[0])
    frontier_pool = frontier_pool[: search_config.beam_width]

    rounds_completed = 0
    candidate_sequence = 0
    for round_idx in range(search_config.max_rounds):
        if not frontier_pool:
            break
        next_frontier_candidates = []

        for _, parent_id, grouping, topology in frontier_pool:
            top_mutations = nsmallest(
                search_config.max_neighbors_per_parent,
                chain(
                    _generate_reassignment_mutations(
                        base_graph,
                        grouping,
                        turbines_by_id,
                        project_input.feeder_capacity_mw,
                    ),
                    _generate_swap_mutations(
                        base_graph,
                        grouping,
                        turbines_by_id,
                        project_input.feeder_capacity_mw,
                    ),
                    _generate_reconnect_mutations(base_graph, topology),
                ),
                key=lambda item: (item[0], repr(item[1])),
            )

            for _, mutation in top_mutations:
                designs_generated += 1

                if isinstance(mutation, EdgeReconnectMutation):
                    new_grouping = grouping
                    new_topology = _apply_topology_mutation(
                        topology, base_graph, mutation
                    )
                elif isinstance(
                    mutation, (FeederReassignmentMutation, FeederSwapMutation)
                ):
                    new_grouping = _apply_grouping_mutation(
                        grouping, turbines_by_id, mutation
                    )
                    new_topology = build_feeder_mst(base_graph, new_grouping)
                else:
                    raise TypeError(f"Unsupported search mutation: {mutation!r}")

                fp = design_fingerprint(new_grouping, new_topology, substation_node_id)
                if fp in evaluated_fingerprints:
                    duplicate_designs_skipped += 1
                    continue

                evaluated_fingerprints.add(fp)

                candidate_sequence += 1
                child_id = f"SCN-S{round_idx + 1}-{candidate_sequence:03d}"
                lineage = CandidateLineage(parent_id, round_idx + 1, mutation)
                parent_parameters = archive[parent_id].scenario.parameters

                scenario, outcome, _ = materialize_candidate_design(
                    topology=new_topology,
                    working_graph=base_graph,
                    cost_surface=cost_surface,
                    project=project_input.project_data,
                    project_id=project_input.project_id,
                    scenario_id=child_id,
                    strategy="SEARCH",
                    parameters=replace(
                        parent_parameters,
                        parameter_set_id=f"SEARCH-{round_idx + 1:02d}",
                        strategy=ScenarioStrategy.SEARCH,
                    ),
                    comparison_group_id=seeds[0].scenario.comparison_group_id
                    if seeds
                    else "search",
                    topology_fingerprint=fp,
                )

                if outcome != AttemptOutcome.ACCEPTED or not scenario:
                    candidates_failed += 1
                    continue

                scenario = replace(scenario, lineage=lineage)
                candidates_evaluated += 1

                eval_res = evaluate_candidate(scenario, project_input, config)
                if (
                    eval_res.execution_failure
                    and eval_res.execution_failure.code
                    == WorkflowFailureCode.UNEXPECTED_EXCEPTION
                ):
                    raise RuntimeError(eval_res.execution_failure.message)
                if eval_res.execution_failure:
                    candidates_failed += 1
                    archive[child_id] = eval_res
                else:
                    archive[child_id] = eval_res
                    next_frontier_candidates.append(
                        (new_grouping, new_topology, child_id)
                    )
        rounds_completed = round_idx + 1
        archive, current_rec = _score_archive(archive, config, electrical_context_id)

        new_frontier = []
        for new_g, new_t, child_id in next_frontier_candidates:
            c = archive[child_id]
            rank = get_rank(c)
            if rank != inf:
                new_frontier.append((rank, child_id, new_g, new_t))

        new_frontier.sort(key=lambda x: x[0])
        frontier_pool = new_frontier[: search_config.beam_width]

    final_rec = current_rec

    final_best_scenario_id = None
    final_route_length = None
    final_lifecycle_cost = None
    if final_rec and final_rec.recommended_scenario_id:
        final_best_scenario_id = final_rec.recommended_scenario_id
        winner = archive[final_best_scenario_id]
        final_route_length = winner.scenario.total_route_length_m
        if winner.cost_assessment and winner.cost_assessment.cost:
            final_lifecycle_cost = float(winner.cost_assessment.cost.lifecycle_cost)

    search_result = CandidateSearchResult(
        rounds_completed=rounds_completed,
        designs_generated=designs_generated,
        duplicate_designs_skipped=duplicate_designs_skipped,
        candidates_evaluated=candidates_evaluated,
        candidates_failed=candidates_failed,
        initial_best_scenario_id=initial_best_scenario_id,
        final_best_scenario_id=final_best_scenario_id,
        initial_route_length_m=initial_route_length,
        final_route_length_m=final_route_length,
        initial_lifecycle_cost=initial_lifecycle_cost,
        final_lifecycle_cost=final_lifecycle_cost,
    )

    return tuple(archive.values()), final_rec, search_result
