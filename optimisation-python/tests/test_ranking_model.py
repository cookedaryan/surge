import joblib
import numpy as np
import pytest
from shapely.geometry import Point
from sklearn.dummy import DummyRegressor

from app.models.spatial import WindTurbine
from app.optimisation.ranking_model import (
    HeuristicRankingModel,
    RankingModelInferenceError,
    SklearnRankingModel,
    build_feature_vector,
    load_ranking_model,
)
from app.optimisation.search_models import (
    EdgeReconnectMutation,
    FeederReassignmentMutation,
    FeederSwapMutation,
    RankingModelConfig,
)


@pytest.fixture
def mock_turbines():
    return {
        "t1": WindTurbine(turbine_id="t1", location=Point(0, 0), capacity_mw=10.0),
        "t2": WindTurbine(turbine_id="t2", location=Point(1, 1), capacity_mw=12.0),
        "t3": WindTurbine(turbine_id="t3", location=Point(2, 2), capacity_mw=15.0),
    }


def test_heuristic_ranking_model_parity(mock_turbines):
    model = HeuristicRankingModel()

    mutation = FeederReassignmentMutation("t1", "f1", "f2")
    feature = build_feature_vector(
        mutation=mutation,
        weight=42.5,
        parent_rank=1.0,
        round_idx=0,
        schema_version="py040-v1",
        turbines_by_id=mock_turbines,
    )
    assert model.score(feature) == 42.5


def test_build_feature_vector_reassignment(mock_turbines):
    mutation = FeederReassignmentMutation("t1", "f1", "f2")
    feature = build_feature_vector(
        mutation=mutation,
        weight=10.0,
        parent_rank=2.0,
        round_idx=1,
        schema_version="py040-v1",
        turbines_by_id=mock_turbines,
    )

    assert feature.mutation_type == "FEEDER_REASSIGNMENT"
    assert feature.capacity_delta_mw == 10.0
    assert feature.edge_weight == 10.0
    assert feature.search_round == 2
    assert feature.parent_rank == 2.0


def test_build_feature_vector_swap(mock_turbines):
    mutation = FeederSwapMutation("t1", "f1", "t2", "f2")
    feature = build_feature_vector(
        mutation=mutation,
        weight=5.0,
        parent_rank=1.0,
        round_idx=0,
        schema_version="py040-v1",
        turbines_by_id=mock_turbines,
    )

    assert feature.mutation_type == "FEEDER_SWAP"
    assert feature.capacity_delta_mw == 2.0  # abs(10.0 - 12.0)


def test_build_feature_vector_reconnect(mock_turbines):
    mutation = EdgeReconnectMutation("f1", ("t1", "t2"), ("t2", "t3"))
    feature = build_feature_vector(
        mutation=mutation,
        weight=15.0,
        parent_rank=1.0,
        round_idx=0,
        schema_version="py040-v1",
        turbines_by_id=mock_turbines,
    )

    assert feature.mutation_type == "EDGE_RECONNECT"
    assert feature.capacity_delta_mw is None


@pytest.fixture
def dummy_model_path(tmp_path):
    model = DummyRegressor(strategy="constant", constant=42.0)
    model.fit(np.zeros((1, 6)), np.zeros(1))
    
    model_dir = tmp_path / "dummy_model"
    model_dir.mkdir()
    
    import json
    from app.optimisation.ml.feature_schema import PRE_RANKER_FEATURE_SCHEMA_VERSION
    with open(model_dir / "metadata.json", "w") as f:
        json.dump({"feature_schema_version": PRE_RANKER_FEATURE_SCHEMA_VERSION}, f)
        
    model_path = model_dir / "model.joblib"
    joblib.dump(model, model_path)
    return str(model_dir)


def test_load_ranking_model_success(dummy_model_path):
    config = RankingModelConfig(enabled=True, model_path=dummy_model_path)
    model = load_ranking_model(config)
    assert isinstance(model, SklearnRankingModel)

    feature = build_feature_vector(
        mutation=FeederReassignmentMutation("t1", "f1", "f2"),
        weight=10.0,
        parent_rank=1.0,
        round_idx=0,
        schema_version="v1",
        turbines_by_id={
            "t1": WindTurbine(turbine_id="t1", location=Point(0, 0), capacity_mw=10.0)
        },
    )
    assert model.score(feature) == 42.0


def test_load_ranking_model_failure_fallback(tmp_path):
    config = RankingModelConfig(
        enabled=True, model_path=str(tmp_path / "missing.joblib")
    )
    model = load_ranking_model(config)
    assert isinstance(model, HeuristicRankingModel)


def test_inference_failure(dummy_model_path, monkeypatch):
    config = RankingModelConfig(enabled=True, model_path=dummy_model_path)
    model = load_ranking_model(config)

    def mock_predict(*args, **kwargs):
        raise ValueError("Simulated inference error")

    monkeypatch.setattr(model._model, "predict", mock_predict)

    feature = build_feature_vector(
        mutation=FeederReassignmentMutation("t1", "f1", "f2"),
        weight=10.0,
        parent_rank=1.0,
        round_idx=0,
        schema_version="v1",
        turbines_by_id={
            "t1": WindTurbine(turbine_id="t1", location=Point(0, 0), capacity_mw=10.0)
        },
    )

    with pytest.raises(RankingModelInferenceError):
        model.score(feature)
