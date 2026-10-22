"""WP2-8: land and environment inputs change rank as declared.

End to end through the real metric path, not through hand-set metric values:
constraint geometry -> ROW analysis -> metric extraction -> scoring explanation -> rank.

Two candidates are identical in every respect except where their routes run: route
A along y = 0 and route B along y = 100, each two 100 m segments. Length, traversal
cost, poles and electrical results are the same for both. So when a rank changes,
the only thing that can have caused it is the one constraint input the test moved.
"""

from types import SimpleNamespace
from typing import Any

import networkx as nx
import pyproj
import pytest
from shapely.geometry import LineString, Point, Polygon

from app.algorithms.pole_placement import PolePlacementConfig
from app.algorithms.wtg_grouping import GroupingObjective
from app.contracts.codes import MetricDirection, ProfilePolicyMode
from app.contracts.profiles import MetricTerm, ProfileDefinition, ProfileId
from app.electrical.load_flow.config import LoadFlowCableType, LoadFlowConfig
from app.electrical.load_flow.models import LoadFlowNetworkResult
from app.gis.constraints import ConstraintLayer, ConstraintMode, ConstraintType
from app.optimisation.engineering_metrics import (
    build_candidate_engineering_metrics,
    extract_spatial_metrics,
)
from app.optimisation.scenario_models import (
    PNCScenario,
    ScenarioParameters,
    ScenarioStrategy,
    TopologyWeightProfile,
)
from app.pnc.models import PNCFeeder, PNCSegment, ProjectPNCNetwork
from app.presentation.explanation import explain_candidates

CRS = pyproj.CRS.from_epsg(32644)
ROUTE_Y = {"A": 0.0, "B": 100.0}
ROW_WIDTH_M = 20.0


# --- Two candidates, identical except for where they run -------------------------


def _scenario(candidate_id: str) -> PNCScenario:
    y = ROUTE_Y[candidate_id]
    segments = (
        PNCSegment(
            segment_id=f"{candidate_id}-SEG-1",
            feeder_id="FDR-1",
            from_node_id="SUB-1",
            to_node_id="WTG-1",
            route_geometry=LineString([(0.0, y), (100.0, y)]),
            route_length_m=100.0,
            traversal_cost=100.0,
            segment_type="substation_to_wtg",
        ),
        PNCSegment(
            segment_id=f"{candidate_id}-SEG-2",
            feeder_id="FDR-1",
            from_node_id="WTG-1",
            to_node_id="WTG-2",
            route_geometry=LineString([(100.0, y), (200.0, y)]),
            route_length_m=100.0,
            traversal_cost=100.0,
            segment_type="wtg_to_wtg",
        ),
    )
    mst = nx.Graph()
    mst.add_edges_from((("SUB-1", "WTG-1"), ("WTG-1", "WTG-2")))
    network = ProjectPNCNetwork(
        project_id="PROJECT-1",
        substation_id="SUB-1",
        substation_geometry=Point(0.0, y),
        feeders=(
            PNCFeeder(
                feeder_id="FDR-1",
                substation_id="SUB-1",
                wtg_ids=("WTG-1", "WTG-2"),
                ordered_node_ids=("SUB-1", "WTG-1", "WTG-2"),
                segments=segments,
                total_length_m=200.0,
                mst_graph=mst,
            ),
        ),
        wtg_coordinates={"WTG-1": Point(100.0, y), "WTG-2": Point(200.0, y)},
        total_route_length_m=200.0,
        feeder_count=1,
        wtg_count=2,
        segment_count=2,
        crs=CRS,
        route_length_by_feeder={"FDR-1": 200.0},
        wtg_count_by_feeder={"FDR-1": 2},
    )
    strategy = ScenarioStrategy.BASELINE
    return PNCScenario(
        scenario_id=candidate_id,
        strategy=strategy.value,
        parameters=ScenarioParameters(
            parameter_set_id="PS-001",
            strategy=strategy,
            grouping_seed=42,
            grouping_objective=GroupingObjective.MINIMIZE_DISTANCE,
            topology_weight_profile=TopologyWeightProfile.DEFAULT,
            topology_penalty=0.0,
            effective_feeder_capacity_mw=10.0,
        ),
        network=network,
        topology_fingerprint=f"v1:{candidate_id}",
        comparison_group_id="CG-1",
        feeder_count=1,
        wtg_count=2,
        segment_count=2,
        total_route_length_m=200.0,
        route_length_by_feeder={"FDR-1": 200.0},
        wtg_count_by_feeder={"FDR-1": 2},
    )


def _load_flow() -> LoadFlowNetworkResult:
    return LoadFlowNetworkResult(
        converged=True,
        is_valid=True,
        solver_algorithm="nr",
        total_generation_mw=10.0,
        slack_power_mw=10.2,
        total_active_loss_mw=0.2,
        total_reactive_loss_mvar=0.1,
        minimum_voltage_pu=0.98,
        maximum_voltage_pu=1.01,
        maximum_loading_percent=62.0,
        buses=(),
        segments=(),
        feeders=(),
        violations=(),
    )


_LOAD_FLOW_CONFIG = LoadFlowConfig(
    nominal_voltage_kv=33.0,
    slack_voltage_pu=1.0,
    min_voltage_pu=0.95,
    max_voltage_pu=1.05,
    system_base_mva=100.0,
    cable_types=(
        LoadFlowCableType(
            cable_type_id="CABLE-1",
            resistance_ohm_per_km=0.1,
            reactance_ohm_per_km=0.1,
            capacitance_nf_per_km=0.2,
            max_current_a=300.0,
        ),
    ),
    default_cable_type_id="CABLE-1",
    segment_cable_type_ids={},
)
_POLE_CONFIG = PolePlacementConfig(
    target_span_m=50.0,
    min_span_m=20.0,
    max_span_m=60.0,
    coordinate_tolerance_m=0.1,
)


# --- Constraint inputs: the only thing each test moves ---------------------------


def _parcel_on(candidate_id: str, layer_id: str = "parcel-1") -> ConstraintLayer:
    """A soft parcel 60 m long, crossing only the named candidate's corridor."""
    y = ROUTE_Y[candidate_id]
    return ConstraintLayer(
        layer_id=layer_id,
        layer_type=ConstraintType.PARCEL,
        mode=ConstraintMode.SOFT_PENALTY,
        geometry=Polygon(
            [(40.0, y - 5), (100.0, y - 5), (100.0, y + 5), (40.0, y + 5)]
        ),
        buffer_m=0.0,
        cost_weight=2.0,
        crs=CRS,
        source_id=f"CADASTRAL-{layer_id}",
        feature_type="parcel",
    )


def _forest_on(
    candidate_id: str,
    *,
    feature_type: str | None = "forest",
) -> ConstraintLayer:
    """A soft forest 60 m long, crossing only the named candidate's corridor."""
    y = ROUTE_Y[candidate_id]
    return ConstraintLayer(
        layer_id="restricted-1",
        layer_type=ConstraintType.RESTRICTED_AREA,
        mode=ConstraintMode.SOFT_PENALTY,
        geometry=Polygon(
            [(120.0, y - 5), (180.0, y - 5), (180.0, y + 5), (120.0, y + 5)]
        ),
        buffer_m=0.0,
        cost_weight=2.0,
        crs=CRS,
        source_id="asset-forest-1",
        feature_type=feature_type,
    )


# --- Profiles -----------------------------------------------------------------------


def _profile(*terms: MetricTerm) -> ProfileDefinition:
    return ProfileDefinition(
        profile_id=ProfileId.BALANCED,
        version="1",
        policy_mode=ProfilePolicyMode.UNIFIED_ENGINEERING,
        terms=list(terms),
    )


def _term(metric: str, weight: str) -> MetricTerm:
    return MetricTerm(
        metric=metric,
        direction=MetricDirection.MINIMISE,
        weight=weight,
        reference_min="0",
        reference_max="5000",
    )


def _land_profile(weight: str = "1") -> ProfileDefinition:
    # Route length is identical for both candidates, so it can never decide the
    # order; it is here so that a zero land weight still leaves a complete score.
    return _profile(
        _term("affected_parcel_row_area_m2", weight), _term("total_route_length_m", "1")
    )


def _environment_profile(weight: str = "1") -> ProfileDefinition:
    return _profile(
        _term("environmental_overlap_m2", weight), _term("total_route_length_m", "1")
    )


# --- The end-to-end ranking --------------------------------------------------------


def _ranks(
    layers: tuple[ConstraintLayer, ...], definition: ProfileDefinition
) -> dict[str, int | None]:
    return {item.candidate_id: item.rank for item in _explain(layers, definition)}


def _scores(
    layers: tuple[ConstraintLayer, ...], definition: ProfileDefinition
) -> dict[str, float | None]:
    """Total scores, for asserting a strict ordering.

    A rank assertion alone can pass vacuously: when two candidates tie, the
    candidate-ID tie-break ranks A first, so any expectation of "A before B" holds
    whether or not the input under test had an effect. A strict score inequality
    cannot be satisfied by a tie.
    """
    return {
        item.candidate_id: item.total_score for item in _explain(layers, definition)
    }


def _explain(
    layers: tuple[ConstraintLayer, ...], definition: ProfileDefinition
) -> list[Any]:
    candidates = []
    for candidate_id in ("A", "B"):
        scenario = _scenario(candidate_id)
        spatial = extract_spatial_metrics(
            scenario.network, layers, row_corridor_width_m=ROW_WIDTH_M
        )
        assessment = build_candidate_engineering_metrics(
            scenario,
            _load_flow(),
            _LOAD_FLOW_CONFIG,
            spatial,
            pole_config=_POLE_CONFIG,
        )
        assert assessment.metrics is not None, assessment.extraction_failures
        candidates.append(_carrier(candidate_id, assessment.metrics))

    return list(explain_candidates(candidates, definition).candidates)


def _carrier(candidate_id: str, metrics: Any) -> Any:
    # The explanation reads a candidate's ID and evaluation only; everything that
    # matters here was produced by the real extraction above.
    return SimpleNamespace(
        scenario=SimpleNamespace(scenario_id=candidate_id),
        evaluation=SimpleNamespace(
            assessment=SimpleNamespace(eligible=True, metrics=metrics),
            lifecycle_cost=None,
        ),
    )


def test_the_two_candidates_are_otherwise_indistinguishable() -> None:
    # Control: with no constraint input at all, nothing separates them, and the
    # deterministic candidate-ID tie-break decides.
    assert _ranks((), _land_profile()) == {"A": 1, "B": 2}
    assert _ranks((), _environment_profile()) == {"A": 1, "B": 2}


# --- Land ----------------------------------------------------------------------------


def test_land_input_on_a_candidate_ranks_it_lower() -> None:
    assert _ranks((_parcel_on("A"),), _land_profile()) == {"A": 2, "B": 1}


def test_moving_only_the_parcel_reverses_the_ranking() -> None:
    # The single changed input is where the parcel sits.
    on_a = _scores((_parcel_on("A"),), _land_profile())
    on_b = _scores((_parcel_on("B"),), _land_profile())

    assert _ranks((_parcel_on("A"),), _land_profile()) == {"A": 2, "B": 1}
    assert _ranks((_parcel_on("B"),), _land_profile()) == {"A": 1, "B": 2}
    assert on_a["B"] > on_a["A"]
    assert on_b["A"] > on_b["B"]


def test_zero_land_weight_removes_the_land_effect() -> None:
    # The same input that moves the ranking at weight 1 ...
    weighted = _scores((_parcel_on("A"),), _land_profile("1"))
    assert weighted["B"] > weighted["A"]
    # ... moves nothing at weight 0: the candidates tie exactly.
    zeroed = _scores((_parcel_on("A"),), _land_profile("0"))
    assert zeroed["A"] == zeroed["B"]


def test_land_input_does_not_move_an_environment_ranking() -> None:
    # A parcel is land, not environment: an environment-only profile ignores it.
    scores = _scores((_parcel_on("A"),), _environment_profile())
    assert scores["A"] == scores["B"]


def test_more_land_taken_ranks_lower_than_less() -> None:
    # Both candidates cross one parcel, so the count cannot tell them apart. The
    # canonical area metric can: A's parcel is twice as long. The longer parcel is on
    # A deliberately, so the expected order is the opposite of the ID tie-break.
    long_on_a = ConstraintLayer(
        layer_id="parcel-2",
        layer_type=ConstraintType.PARCEL,
        mode=ConstraintMode.SOFT_PENALTY,
        geometry=Polygon([(40.0, -5.0), (160.0, -5.0), (160.0, 5.0), (40.0, 5.0)]),
        buffer_m=0.0,
        cost_weight=2.0,
        crs=CRS,
        source_id="CADASTRAL-parcel-2",
        feature_type="parcel",
    )
    layers = (long_on_a, _parcel_on("B"))

    assert _ranks(layers, _land_profile()) == {"A": 2, "B": 1}
    scores = _scores(layers, _land_profile())
    assert scores["B"] > scores["A"]


# --- Environment -------------------------------------------------------------------


def test_environment_input_on_a_candidate_ranks_it_lower() -> None:
    assert _ranks((_forest_on("A"),), _environment_profile()) == {"A": 2, "B": 1}


def test_moving_only_the_forest_reverses_the_ranking() -> None:
    on_a = _scores((_forest_on("A"),), _environment_profile())
    on_b = _scores((_forest_on("B"),), _environment_profile())

    assert _ranks((_forest_on("A"),), _environment_profile()) == {"A": 2, "B": 1}
    assert _ranks((_forest_on("B"),), _environment_profile()) == {"A": 1, "B": 2}
    assert on_a["B"] > on_a["A"]
    assert on_b["A"] > on_b["B"]


def test_zero_environment_weight_removes_the_environment_effect() -> None:
    weighted = _scores((_forest_on("A"),), _environment_profile("1"))
    assert weighted["B"] > weighted["A"]
    zeroed = _scores((_forest_on("A"),), _environment_profile("0"))
    assert zeroed["A"] == zeroed["B"]


def test_environment_input_does_not_move_a_land_ranking() -> None:
    scores = _scores((_forest_on("A"),), _land_profile())
    assert scores["A"] == scores["B"]


def test_the_environment_effect_depends_on_typed_identity() -> None:
    # Without WP2-4's typed identity the forest is a generic restricted area and is
    # invisible to the environmental metric, which is finding F7. The same geometry
    # with its identity attached is what makes the ranking respond.
    untyped = (_forest_on("A", feature_type=None),)
    typed = (_forest_on("A"),)

    untyped_scores = _scores(untyped, _environment_profile())
    assert untyped_scores["A"] == untyped_scores["B"]
    assert _ranks(typed, _environment_profile()) == {"A": 2, "B": 1}


@pytest.mark.parametrize("candidate_id", ["A", "B"])
def test_land_and_environment_effects_are_independent(candidate_id: str) -> None:
    # Both inputs on the same candidate: each single-objective profile sees exactly
    # its own input and ranks that candidate lower, and only that.
    other = "B" if candidate_id == "A" else "A"
    layers = (_parcel_on(candidate_id), _forest_on(candidate_id))

    expected = {candidate_id: 2, other: 1}
    for profile in (_land_profile(), _environment_profile()):
        assert _ranks(layers, profile) == expected
        scores = _scores(layers, profile)
        assert scores[other] > scores[candidate_id]
