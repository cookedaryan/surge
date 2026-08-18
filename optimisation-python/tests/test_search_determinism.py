"""Tests for determinism in search."""

import json
from dataclasses import replace
from pathlib import Path
from typing import Any, cast

import joblib
import networkx as nx
import numpy as np
import pytest
from shapely.geometry import Point
from sklearn.dummy import DummyRegressor

from app.algorithms.topology import CollectorTopologyResult, FeederTopology
from app.algorithms.wtg_grouping import FeederAssignment, FeederGroupingResult
from app.optimisation.orchestrator import optimise_project
from app.optimisation.scenarios import design_fingerprint
from app.optimisation.search_models import RankingModelConfig
from app.schemas.v2.domain_mapping import to_workflow_invocation
from app.schemas.v2.optimise import OptimiseProjectRequest

JsonObject = dict[str, Any]


def test_hash_candidate_topology_is_order_independent() -> None:
    # Two identical networks constructed in different order
    mst = nx.Graph()
    mst.add_edges_from([("A", "B"), ("C", "D")])

    t1 = FeederTopology(
        feeder_id="F1",
        node_ids=("A", "B"),
        total_capacity_mw=1.0,
        total_length_m=1.0,
        mst_edges=(("A", "B"),),
        mst_graph=mst,
    )
    t2 = FeederTopology(
        feeder_id="F2",
        node_ids=("C", "D"),
        total_capacity_mw=1.0,
        total_length_m=1.0,
        mst_edges=(("C", "D"),),
        mst_graph=mst,
    )

    topology1 = CollectorTopologyResult(feeders=(t1, t2))
    topology2 = CollectorTopologyResult(feeders=(t2, t1))

    grouping1 = FeederGroupingResult(
        2,
        (
            FeederAssignment("F1", ("A", "B"), 1.0, Point(0, 0)),
            FeederAssignment("F2", ("C", "D"), 1.0, Point(1, 1)),
        ),
    )
    grouping2 = FeederGroupingResult(
        2,
        (
            FeederAssignment("F2", ("C", "D"), 1.0, Point(1, 1)),
            FeederAssignment("F1", ("A", "B"), 1.0, Point(0, 0)),
        ),
    )

    h1 = design_fingerprint(grouping1, topology1, "SUB")
    h2 = design_fingerprint(grouping2, topology2, "SUB")

    assert h1 == h2


@pytest.fixture
def dummy_model_path(tmp_path: Path) -> str:
    model = DummyRegressor(strategy="constant", constant=42.0)
    model.fit(np.zeros((1, 6)), np.zeros(1))
    
    model_dir = tmp_path / "dummy_model"
    model_dir.mkdir()
    
    from app.optimisation.ml.feature_schema import PRE_RANKER_FEATURE_SCHEMA_VERSION
    with open(model_dir / "metadata.json", "w") as f:
        json.dump({"feature_schema_version": PRE_RANKER_FEATURE_SCHEMA_VERSION}, f)
        
    model_path = model_dir / "model.joblib"
    joblib.dump(model, model_path)
    return str(model_dir)


def test_ranking_model_disabled_parity() -> None:
    fixture_path = (
        Path(__file__).parent / "fixtures" / "corpus" / "SYN-4-SPREAD-30.json"
    )
    payload = cast(JsonObject, json.loads(fixture_path.read_text(encoding="utf-8")))
    invocation = to_workflow_invocation(OptimiseProjectRequest.model_validate(payload))

    # Run once with default (disabled) ranking model
    search_default = replace(
        invocation.config.search,
        enabled=True,
        max_rounds=1,
        beam_width=1,
        max_search_evaluations=5,
        max_candidate_proposals=5,
    )
    config_default = replace(invocation.config, search=search_default)
    result_default = optimise_project(invocation.project_input, config_default)

    # Run explicitly disabled
    ranking_disabled = RankingModelConfig(enabled=False)
    search_disabled = replace(search_default, ranking_model=ranking_disabled)
    config_disabled = replace(invocation.config, search=search_disabled)
    result_disabled = optimise_project(invocation.project_input, config_disabled)

    assert result_default.status == result_disabled.status
    if result_default.recommendation:
        assert result_disabled.recommendation is not None
        assert (
            result_default.recommendation.recommended_scenario_id
            == result_disabled.recommendation.recommended_scenario_id
        )
    assert result_default.search_result is not None
    assert result_disabled.search_result is not None
    assert len(result_default.search_result.statistics.termination_reason) > 0
    assert (
        result_default.search_result.rounds_completed
        == result_disabled.search_result.rounds_completed
    )
    assert (
        result_default.search_result.statistics.unique_count
        == result_disabled.search_result.statistics.unique_count
    )


def test_ranking_model_enabled_determinism(dummy_model_path: str) -> None:
    fixture_path = (
        Path(__file__).parent / "fixtures" / "corpus" / "SYN-4-SPREAD-30.json"
    )
    payload = cast(JsonObject, json.loads(fixture_path.read_text(encoding="utf-8")))
    invocation = to_workflow_invocation(OptimiseProjectRequest.model_validate(payload))

    ranking_enabled = RankingModelConfig(enabled=True, model_path=dummy_model_path)
    search_config = replace(
        invocation.config.search,
        enabled=True,
        max_rounds=1,
        beam_width=1,
        max_search_evaluations=5,
        max_candidate_proposals=5,
        ranking_model=ranking_enabled,
    )
    config = replace(invocation.config, search=search_config)

    result1 = optimise_project(invocation.project_input, config)
    result2 = optimise_project(invocation.project_input, config)

    assert result1.status == result2.status
    if result1.recommendation:
        assert result2.recommendation is not None
        assert (
            result1.recommendation.recommended_scenario_id
            == result2.recommendation.recommended_scenario_id
        )
    assert result1.search_result is not None
    assert result2.search_result is not None
    assert result1.search_result.statistics.ranking_model_enabled is True
    assert result1.search_result.statistics.ranking_model_loaded is True
    assert result1.search_result.statistics.model_rank_calls > 0
    assert result1.search_result.statistics.model_ranked_mutations > 0
    assert result1.search_result.statistics.model_fallback_count == 0
    assert (
        result1.search_result.statistics.unique_count
        == result2.search_result.statistics.unique_count
    )
