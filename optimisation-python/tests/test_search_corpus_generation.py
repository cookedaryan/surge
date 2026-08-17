import csv
import json
from pathlib import Path
from typing import Any, cast

import pytest

from app.algorithms.route_graph import build_project_graph
from app.algorithms.wtg_grouping import FeederAssignment, FeederGroupingResult
from app.optimisation.candidate_search import _compute_mutation_features
from app.optimisation.corpus.synthetic_projects import (
    PROJECT_SPECS,
    generate_synthetic_projects,
)
from app.optimisation.search_models import EdgeReconnectMutation
from app.schemas.v2.domain_mapping import to_workflow_invocation
from app.schemas.v2.optimise import OptimiseProjectRequest
from tests.fixtures.demo_project import build_demo_project_data

JsonObject = dict[str, Any]


def test_synthetic_projects_are_deterministic_and_vary_capacity(
    tmp_path: Path,
) -> None:
    first_dir = tmp_path / "first"
    second_dir = tmp_path / "second"
    first_paths = generate_synthetic_projects(first_dir)
    second_paths = generate_synthetic_projects(second_dir)

    assert [path.name for path in first_paths] == [path.name for path in second_paths]
    assert [path.read_bytes() for path in first_paths] == [
        path.read_bytes() for path in second_paths
    ]

    feeder_capacities = set()
    turbine_counts = set()
    for path in first_paths:
        payload = cast(JsonObject, json.loads(path.read_text(encoding="utf-8")))
        request = OptimiseProjectRequest.model_validate(payload)
        invocation = to_workflow_invocation(request)
        feeder_capacities.add(invocation.project_input.feeder_capacity_mw)
        turbine_counts.add(len(invocation.project_input.project_data.turbines))
        assert request.costing_config is not None
        assert request.cost_aware_config is not None

    assert len(feeder_capacities) == len(PROJECT_SPECS)
    assert turbine_counts == {8, 12, 20, 30, 40}


def test_reconnect_feature_uses_added_edge_weight() -> None:
    project = build_demo_project_data()
    graph = build_project_graph(project)
    turbine_ids = tuple(turbine.turbine_id for turbine in project.turbines)
    grouping = FeederGroupingResult(
        feeder_count=1,
        assignments=(
            FeederAssignment(
                feeder_id="F1",
                turbine_ids=turbine_ids,
                total_capacity_mw=40.0,
                centroid=project.substation.location,
            ),
        ),
    )
    mutation = EdgeReconnectMutation(
        feeder_id="F1",
        removed_edge=("wtg:T01", "wtg:T02"),
        added_edge=("wtg:T03", "wtg:T04"),
    )
    features = _compute_mutation_features(
        mutation=mutation,
        mutation_weight=-123.0,
        parent_rank=1.0,
        grouping=grouping,
        turbines_by_id={t.turbine_id: t for t in project.turbines},
        base_graph=graph,
    )

    expected_weight = graph["wtg:T03"]["wtg:T04"]["weight"]
    assert features["edge_weight"] == pytest.approx(expected_weight)
    assert features["edge_weight"] != -123.0
    assert features["turbine_dispersion_stddev"] != 0.0


def test_generated_corpus_has_all_projects_and_labels() -> None:
    corpus_path = Path(__file__).parents[1] / "search_corpus.csv"
    with open(corpus_path, newline="", encoding="utf-8") as corpus_file:
        rows = list(csv.DictReader(corpus_file))

    assert rows
    assert {row["project_id"] for row in rows} == {
        spec.project_id for spec in PROJECT_SPECS
    }
    assert "edge_weight" in rows[0]
    assert "heuristic_score" not in rows[0]
    for row in rows:
        assert row["evaluation.rank"]
        assert row["feasible"] in {"True", "False"}
        assert row["evaluation.lifecycle_cost"]
        assert row["total_route_length_m"]
