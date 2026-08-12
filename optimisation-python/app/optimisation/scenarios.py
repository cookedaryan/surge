"""Deterministic candidate PNC scenario generation — SURGE-PY-017.

Public API
----------
generate_pnc_scenarios(project_data, feeder_capacity_mw, cost_surface, config)
    Generate a configurable set of distinct, valid PNC network candidates.

scenario_fingerprint(network)
    Compute a stable SHA-256 topology fingerprint for duplicate detection.

topology_fingerprint_from_grouping(grouping, graph)
    Compute a topology fingerprint from a grouping + graph before running A*,
    allowing early duplicate suppression before expensive routing.

Internal helpers (prefixed with _) are not part of the public API.

Design principles
-----------------
1.  Every candidate flows through the real algorithm pipeline:
        group_wtgs → build_project_graph → (reweight) → build_feeder_mst
        → route_collector_topology → refine_routing_result
        → assemble_pnc_network
    No finished networks are mutated.

2.  Duplicate suppression happens *before* physical routing (A*) using a
    topology-level fingerprint computed from feeder WTG memberships and MST
    edges.  This avoids up to candidate_count × 4 unnecessary A* runs.

3.  The base graph is built once and never mutated.  Reweighted copies are
    created with graph.copy() before any transformation.

4.  Only known candidate-specific failures (routing failure, assembly
    failure, grouping failure) are swallowed and recorded.  Configuration
    errors and unexpected exceptions propagate to the caller.

5.  Fewer candidates than requested is a valid result.  Zero candidates
    raises NoValidScenarioError.

Fingerprint schema v1
---------------------
topology_fingerprint encodes:

    "v1:" + sha256(canonical_json(feeder_records))

where feeder_records is a sorted list of:

    {"edges": sorted_edge_list, "wtgs": sorted_wtg_list}

Feeders are sorted by their canonical content (not feeder ID) so that an
equivalent partition with different labels produces the same fingerprint.
"""

from __future__ import annotations

import hashlib
import json
import math

import networkx as nx

from app.algorithms.physical_routing import RouteNotFoundError, route_collector_topology
from app.algorithms.route_graph import build_project_graph
from app.algorithms.route_refinement import refine_routing_result
from app.algorithms.topology import CollectorTopologyResult, build_feeder_mst
from app.algorithms.wtg_grouping import (
    FeederGroupingResult,
    group_wtgs,
)
from app.gis.cost_surface import CostSurface
from app.models.spatial import ProjectSpatialData
from app.optimisation.scenario_models import (
    PARAMETER_SCHEDULE,
    AttemptOutcome,
    NoValidScenarioError,
    PNCScenario,
    ScenarioAttempt,
    ScenarioGenerationConfig,
    ScenarioGenerationResult,
    ScenarioParameters,
    TopologyWeightProfile,
)
from app.pnc.assembly import assemble_pnc_network
from app.pnc.errors import PNCAssemblyError
from app.pnc.models import ProjectPNCNetwork

# ---------------------------------------------------------------------------
# Fingerprinting
# ---------------------------------------------------------------------------

_FINGERPRINT_SCHEMA = "v1"


def _canonical_feeder_record(
    wtg_node_ids: frozenset[str],
    mst_edges: tuple[tuple[str, str], ...],
) -> dict[str, list[str]]:
    """Build a canonical dict for one feeder.

    Edges are represented as sorted endpoint pairs to eliminate direction;
    the list of edge-pairs is then sorted for stable ordering.
    """
    canonical_edges = sorted([sorted([u, v]) for u, v in mst_edges])
    return {
        "wtgs": sorted(wtg_node_ids),
        "edges": [f"{u}:{v}" for u, v in canonical_edges],
    }


def _fingerprint_feeder_records(
    feeder_records: list[dict[str, list[str]]],
) -> str:
    """Compute a stable SHA-256 fingerprint over a list of feeder records.

    Feeder records are sorted by their canonical content (not feeder ID) so
    that relabelled-but-equivalent partitions produce the same fingerprint.
    """
    # Sort feeder records by their serialised form to make order independent
    # of feeder ID labelling.
    sorted_records = sorted(
        feeder_records,
        key=lambda r: (r["wtgs"], r["edges"]),
    )
    payload = json.dumps(sorted_records, sort_keys=True, separators=(",", ":"))
    digest = hashlib.sha256(payload.encode("utf-8")).hexdigest()
    return f"{_FINGERPRINT_SCHEMA}:{digest}"


def scenario_fingerprint(network: ProjectPNCNetwork) -> str:
    """Compute a stable topology fingerprint for a ``ProjectPNCNetwork``.

    The fingerprint encodes feeder WTG memberships and MST edges.  It does
    not encode physical route geometry, because identical topology + cost
    surface always produces identical routing.

    Feeders are sorted by canonical content (not feeder ID) so that an
    equivalent partition with different labels produces the same fingerprint.

    Returns
    -------
    str
        ``"v1:<sha256hex>"``
    """
    feeder_records: list[dict[str, list[str]]] = []
    for feeder in network.feeders:
        wtg_ids = frozenset(feeder.wtg_ids)
        mst_edges = tuple(feeder.mst_graph.edges())
        feeder_records.append(_canonical_feeder_record(wtg_ids, mst_edges))
    return _fingerprint_feeder_records(feeder_records)


def _topology_fingerprint_from_grouping_and_mst(
    grouping: FeederGroupingResult,
    topology: CollectorTopologyResult,
    substation_node_id: str,
) -> str:
    """Compute a topology fingerprint before physical routing.

    Used for early duplicate suppression to avoid running A* on a topology
    that is structurally identical to an already-accepted candidate.
    """
    feeder_records: list[dict[str, list[str]]] = []
    for ft in topology.feeders:
        wtg_ids = frozenset(n for n in ft.node_ids if n != substation_node_id)
        mst_edges = ft.mst_edges
        feeder_records.append(_canonical_feeder_record(wtg_ids, mst_edges))
    return _fingerprint_feeder_records(feeder_records)


# ---------------------------------------------------------------------------
# Graph reweighting for LONG_EDGE_PENALTY strategy
# ---------------------------------------------------------------------------


def _apply_long_edge_penalty(
    graph: nx.Graph,
    alpha: float,
) -> nx.Graph:
    """Return a copy of *graph* with non-uniform edge weights.

    Transformation: ``w' = w * (1 + alpha * w / w_max)``

    This is a strictly convex amplification.  Longer edges are penalised by
    a larger *relative* factor than shorter edges, which breaks the
    weight-scaling symmetry and can change the MST.

    The base graph is never mutated; a copy is returned.

    Parameters
    ----------
    graph:
        The project topology graph produced by ``build_project_graph``.
    alpha:
        Amplification factor.  ``alpha=0`` leaves weights unchanged.
        ``alpha=2`` is the default for the LONG_EDGE_PENALTY strategy.
    """
    if alpha == 0.0:
        return graph

    g = graph.copy()

    # Find the maximum finite edge weight
    weights = [
        data.get("weight", 0.0)
        for _, _, data in g.edges(data=True)
        if math.isfinite(data.get("weight", 0.0))
    ]
    if not weights:
        return g

    w_max = max(weights)
    if w_max <= 0.0:
        return g

    for u, v, data in g.edges(data=True):
        w = data.get("weight", 0.0)
        if math.isfinite(w):
            new_w = w * (1.0 + alpha * w / w_max)
            g[u][v]["weight"] = new_w

    return g


# ---------------------------------------------------------------------------
# Parameter schedule materialisation
# ---------------------------------------------------------------------------


def _build_scenario_parameters(
    feeder_capacity_mw: float,
    n_candidates: int,
) -> tuple[ScenarioParameters, ...]:
    """Materialise ``ScenarioParameters`` for the first *n_candidates* entries
    in ``PARAMETER_SCHEDULE``.

    This is the single source of truth for the deterministic parameter
    schedule.  The result is always a prefix of ``PARAMETER_SCHEDULE``
    — never a permutation or random subset.
    """
    params: list[ScenarioParameters] = []
    for entry in PARAMETER_SCHEDULE[:n_candidates]:
        ps_id, strategy, seed, obj, weight_profile, penalty = entry
        params.append(
            ScenarioParameters(
                parameter_set_id=ps_id,
                strategy=strategy,
                grouping_seed=seed,
                grouping_objective=obj,
                topology_weight_profile=weight_profile,
                topology_penalty=penalty,
                effective_feeder_capacity_mw=feeder_capacity_mw,
            )
        )
    return tuple(params)


# ---------------------------------------------------------------------------
# Single-candidate private pipeline
# ---------------------------------------------------------------------------


def _generate_candidate(
    project: ProjectSpatialData,
    feeder_capacity_mw: float,
    cost_surface: CostSurface,
    project_id: str,
    parameters: ScenarioParameters,
    base_graph: nx.Graph,
    substation_node: str,
    accepted_fingerprints: set[str],
) -> tuple[ProjectPNCNetwork | None, str | None, AttemptOutcome, str]:
    """Run the full PNC pipeline for one set of scenario parameters.

    Returns
    -------
    (network, fingerprint, outcome, detail)

    ``network`` and ``fingerprint`` are ``None`` when the candidate was not
    accepted.

    The base graph and project data are never mutated.

    Only candidate-specific failures are caught:
    - Grouping failure (ValueError from group_wtgs)
    - Routing failure (RouteNotFoundError)
    - Assembly failure (PNCAssemblyError, ValueError from assemble_pnc_network)

    All other exceptions propagate to the caller.
    """
    # 1. WTG grouping --------------------------------------------------
    try:
        grouping = group_wtgs(
            project,
            feeder_capacity_mw,
            random_state=parameters.grouping_seed,
            objective=parameters.grouping_objective,
        )
    except ValueError as exc:
        return None, None, AttemptOutcome.GROUPING_FAILED, str(exc)

    if not grouping.assignments:
        return (
            None,
            None,
            AttemptOutcome.GROUPING_FAILED,
            "Grouping produced zero feeder assignments",
        )

    # 2. Graph (reweight if necessary) ---------------------------------
    if parameters.topology_weight_profile == TopologyWeightProfile.LONG_EDGE_PENALTY:
        working_graph = _apply_long_edge_penalty(
            base_graph, parameters.topology_penalty
        )
    else:
        working_graph = base_graph  # read-only; topology does not modify it

    # 3. MST topology --------------------------------------------------
    topology: CollectorTopologyResult = build_feeder_mst(working_graph, grouping)

    # 4. Topology fingerprint — early duplicate suppression before A* --
    topo_fp = _topology_fingerprint_from_grouping_and_mst(
        grouping, topology, substation_node
    )
    if topo_fp in accepted_fingerprints:
        return (
            None,
            topo_fp,
            AttemptOutcome.DUPLICATE_TOPOLOGY,
            "Topology already accepted",
        )

    # 5. Physical routing (A*) ----------------------------------------
    try:
        physical_routes = route_collector_topology(
            topology, working_graph, cost_surface
        )
        refined_routes = refine_routing_result(physical_routes, cost_surface)
    except RouteNotFoundError as exc:
        return None, topo_fp, AttemptOutcome.ROUTING_FAILED, str(exc)

    # 6. PNC assembly -------------------------------------------------
    try:
        network = assemble_pnc_network(
            project_id=project_id,
            project=project,
            topology=topology,
            refined_routes=refined_routes,
        )
    except (PNCAssemblyError, ValueError) as exc:
        return None, topo_fp, AttemptOutcome.ASSEMBLY_FAILED, str(exc)

    # 7. Final network fingerprint (should match topology fingerprint) --
    net_fp = scenario_fingerprint(network)
    # If the final fingerprint collides with an accepted one, suppress.
    if net_fp in accepted_fingerprints:
        return (
            None,
            net_fp,
            AttemptOutcome.DUPLICATE_TOPOLOGY,
            "Network fingerprint already accepted",
        )

    return network, net_fp, AttemptOutcome.ACCEPTED, ""


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------


def generate_pnc_scenarios(
    project_data: ProjectSpatialData,
    feeder_capacity_mw: float,
    cost_surface: CostSurface,
    config: ScenarioGenerationConfig | None = None,
) -> ScenarioGenerationResult:
    """Generate a configurable set of deterministic PNC network candidates.

    If *config* is ``None``, ``ScenarioGenerationConfig()`` defaults are used.

    Given the same ``project_data``, ``feeder_capacity_mw``, ``cost_surface``,
    and ``config``, this function always returns the same candidates in the
    same order with the same fingerprints (provided the underlying algorithms
    are deterministic).

    Parameters
    ----------
    project_data:
        Spatial data (WTGs + substation) in a projected CRS.
    feeder_capacity_mw:
        Maximum electrical capacity per feeder (MW).  Passed unchanged to
        every grouping call — scenario generation never silently alters this.
    cost_surface:
        Raster cost surface used by A* physical routing.
    config:
        Controls candidate count, seed, and project ID.

    Returns
    -------
    ScenarioGenerationResult
        Contains all accepted ``PNCScenario`` objects plus per-attempt
        diagnostics.  Raises ``NoValidScenarioError`` if zero candidates
        could be generated.

    Raises
    ------
    NoValidScenarioError
        Zero valid PNC candidates were produced.  This is an explicit
        generation failure.
    InvalidScenarioConfigError
        ``config`` failed validation (raised by ``ScenarioGenerationConfig``).
    Exception
        Any unexpected (non-candidate-specific) exception propagates.

    PNC validity definition
    -----------------------
    A candidate is PNC-valid when grouping, topology, physical routing,
    refinement, and PNC assembly all succeed.  Electrical and scoring
    feasibility are evaluated by later stages (PY-015, PY-018).
    """
    if not math.isfinite(feeder_capacity_mw) or feeder_capacity_mw <= 0.0:
        raise ValueError(
            f"feeder_capacity_mw must be positive and finite, got {feeder_capacity_mw}"
        )

    # Resolve config defaults.
    if config is None:
        config = ScenarioGenerationConfig()

    # Stable comparison group ID for this generation run.
    # Uses the project_id + config repr so it is deterministic.
    comparison_group_id = (
        f"{config.project_id}:{config.candidate_count}:{config.base_seed}"
    )

    # Build the base project graph once.  Never mutate it.
    base_graph: nx.Graph = build_project_graph(project_data)

    # Identify substation node ID for fingerprinting.
    substations = [
        n for n, d in base_graph.nodes(data=True) if d.get("type") == "substation"
    ]
    if not substations:
        raise ValueError("Project graph contains no substation node")
    substation_node = substations[0]

    # Materialise the parameter schedule for all 5 entries.
    # The generator stops when it has collected enough or exhausted the schedule.
    all_parameters = _build_scenario_parameters(
        feeder_capacity_mw, len(PARAMETER_SCHEDULE)
    )

    accepted_fingerprints: set[str] = set()
    candidates: list[PNCScenario] = []
    attempts: list[ScenarioAttempt] = []
    scenario_counter = 0

    # Bounded loop: try each entry in the full schedule in order.
    # Stop when we have collected enough accepted candidates or exhausted the schedule.
    for parameters in all_parameters:
        if len(candidates) >= config.candidate_count:
            break

        network, fingerprint, outcome, detail = _generate_candidate(
            project=project_data,
            feeder_capacity_mw=feeder_capacity_mw,
            cost_surface=cost_surface,
            project_id=config.project_id,
            parameters=parameters,
            base_graph=base_graph,
            substation_node=substation_node,
            accepted_fingerprints=accepted_fingerprints,
        )

        attempts.append(
            ScenarioAttempt(
                parameter_set_id=parameters.parameter_set_id,
                strategy=parameters.strategy,
                outcome=outcome,
                topology_fingerprint=fingerprint,
                detail=detail,
            )
        )

        if (
            outcome == AttemptOutcome.ACCEPTED
            and network is not None
            and fingerprint is not None
        ):
            scenario_counter += 1
            scenario_id = f"SCN-{scenario_counter:03d}"
            accepted_fingerprints.add(fingerprint)

            scenario = PNCScenario(
                scenario_id=scenario_id,
                strategy=parameters.strategy,
                parameters=parameters,
                network=network,
                topology_fingerprint=fingerprint,
                comparison_group_id=comparison_group_id,
                feeder_count=network.feeder_count,
                wtg_count=network.wtg_count,
                segment_count=network.segment_count,
                total_route_length_m=network.total_route_length_m,
                route_length_by_feeder=network.route_length_by_feeder,
                wtg_count_by_feeder=network.wtg_count_by_feeder,
            )
            candidates.append(scenario)

    if not candidates:
        raise NoValidScenarioError(
            f"No valid PNC scenario could be generated for project "
            f"{config.project_id!r}. "
            f"Attempted {len(attempts)} parameter set(s). "
            f"See attempts for details: "
            + "; ".join(
                f"{a.parameter_set_id}={a.outcome}({a.detail})" for a in attempts
            )
        )

    return ScenarioGenerationResult(
        requested_candidate_count=config.candidate_count,
        candidates=tuple(candidates),
        attempts=tuple(attempts),
        comparison_group_id=comparison_group_id,
    )
