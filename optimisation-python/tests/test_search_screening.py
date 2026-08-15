"""Tests for structural screening during search."""

import networkx as nx
from shapely.geometry import Point

from app.algorithms.topology import CollectorTopologyResult, FeederTopology
from app.algorithms.wtg_grouping import FeederAssignment, FeederGroupingResult
from app.models.spatial import ProjectSpatialData, Substation, WindTurbine
from app.optimisation.candidate_validation import validate_candidate_structure
from app.optimisation.workflow_models import ProjectInput


def test_structural_screening_rejects_cycles():
    # Simple cycle A -> B -> C -> A
    mst = nx.Graph()
    mst.add_edges_from([("wtg:A", "wtg:B"), ("wtg:B", "wtg:C"), ("wtg:C", "wtg:A")])

    topology = CollectorTopologyResult(
        feeders=(
            FeederTopology(
                feeder_id="F1",
                node_ids=("wtg:A", "wtg:B", "wtg:C"),
                total_capacity_mw=10.0,
                total_length_m=3.0,
                mst_edges=(("wtg:A", "wtg:B"), ("wtg:B", "wtg:C"), ("wtg:C", "wtg:A")),
                mst_graph=mst,
            ),
        )
    )

    grouping = FeederGroupingResult(
        1, (FeederAssignment("F1", ("A", "B", "C"), 10.0, Point(0, 0)),)
    )

    project_input = ProjectInput(
        project_id="PROJ-DEMO",
        project_data=ProjectSpatialData(
            substation=Substation(substation_id="SUB", location=Point(10, 10)),
            turbines=(
                WindTurbine(turbine_id="A", location=Point(0, 0), capacity_mw=3.0),
                WindTurbine(turbine_id="B", location=Point(1, 1), capacity_mw=3.0),
                WindTurbine(turbine_id="C", location=Point(2, 2), capacity_mw=4.0),
            ),
            projected_crs="EPSG:32631",
        ),
        constraint_layers=(),
        cost_surface=None,
        feeder_capacity_mw=100.0,
        operating_points=(),
    )

    is_valid = validate_candidate_structure(grouping, topology, project_input, "SUB")
    assert not is_valid


def test_structural_screening_accepts_valid_tree():
    mst = nx.Graph()
    mst.add_edges_from([("SUB", "wtg:A"), ("wtg:A", "wtg:B")])

    topology = CollectorTopologyResult(
        feeders=(
            FeederTopology(
                feeder_id="F1",
                node_ids=("SUB", "wtg:A", "wtg:B"),
                total_capacity_mw=10.0,
                total_length_m=2.0,
                mst_edges=(("wtg:A", "wtg:B"), ("wtg:A", "SUB")),
                mst_graph=mst,
            ),
        )
    )

    grouping = FeederGroupingResult(
        1, (FeederAssignment("F1", ("A", "B"), 10.0, Point(0, 0)),)
    )

    project_input = ProjectInput(
        project_id="PROJ-DEMO",
        project_data=ProjectSpatialData(
            substation=Substation(substation_id="SUB", location=Point(10, 10)),
            turbines=(
                WindTurbine(turbine_id="A", location=Point(0, 0), capacity_mw=5.0),
                WindTurbine(turbine_id="B", location=Point(1, 1), capacity_mw=5.0),
            ),
            projected_crs="EPSG:32631",
        ),
        constraint_layers=(),
        cost_surface=None,
        feeder_capacity_mw=100.0,
        operating_points=(),
    )

    is_valid = validate_candidate_structure(grouping, topology, project_input, "SUB")
    assert is_valid
