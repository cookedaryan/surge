import numpy as np

from app.optimisation.ml.feature_schema import MODEL_FEATURES
from app.optimisation.ml.training import (
    build_pipeline,
    cross_validate_model,
    train_final_model,
)


def test_pipeline_construction():
    pipe = build_pipeline("ridge", 42)
    assert pipe.named_steps["preprocessor"]
    assert pipe.named_steps["estimator"].__class__.__name__ == "Ridge"

    pipe2 = build_pipeline("hist_gb", 42)
    assert (
        pipe2.named_steps["estimator"].__class__.__name__
        == "HistGradientBoostingRegressor"
    )


def test_project_isolated_folds(monkeypatch):
    rows = [
        {
            "project_id": "P1",
            "relative_quality": 0.0,
            "heuristic_score": 10,
            "scenario_id": "1",
            "round_idx": 1,
            "parent_id": "X",
        },
        {
            "project_id": "P1",
            "relative_quality": 1.0,
            "heuristic_score": 10,
            "scenario_id": "2",
            "round_idx": 1,
            "parent_id": "X",
        },
        {
            "project_id": "P2",
            "relative_quality": 0.0,
            "heuristic_score": 20,
            "scenario_id": "3",
            "round_idx": 1,
            "parent_id": "X",
        },
        {
            "project_id": "P2",
            "relative_quality": 1.0,
            "heuristic_score": 20,
            "scenario_id": "4",
            "round_idx": 1,
            "parent_id": "X",
        },
        {
            "project_id": "P3",
            "relative_quality": 0.0,
            "heuristic_score": 30,
            "scenario_id": "5",
            "round_idx": 1,
            "parent_id": "X",
        },
        {
            "project_id": "P3",
            "relative_quality": 1.0,
            "heuristic_score": 30,
            "scenario_id": "6",
            "round_idx": 1,
            "parent_id": "X",
        },
    ]

    calls = []

    class DummyPipeline:
        def fit(self, x, y):
            calls.append(("fit", set(x["heuristic_score"])))

        def predict(self, x):
            calls.append(("predict", set(x["heuristic_score"])))
            return np.zeros(len(x))

    monkeypatch.setattr(
        "app.optimisation.ml.training.build_pipeline", lambda m, s: DummyPipeline()
    )

    cross_validate_model("ridge", rows, 2)

    assert len(calls) == 6  # 3 folds * (fit + predict)

    for i in range(0, 6, 2):
        fit_projects = calls[i][1]
        test_projects = calls[i + 1][1]
        assert fit_projects.isdisjoint(test_projects)


def test_final_pipeline_records_only_declared_model_features():
    rows = [
        {
            **{feature: 0.0 for feature in MODEL_FEATURES},
            "mutation_type": "EDGE_RECONNECT",
            "relative_quality": 0.0,
            "project_id": "must-not-be-an-input-feature",
        },
        {
            **{feature: 1.0 for feature in MODEL_FEATURES},
            "mutation_type": "FEEDER_SWAP",
            "relative_quality": 1.0,
            "project_id": "must-not-be-an-input-feature",
        },
    ]

    pipeline = train_final_model("ridge", rows)

    assert tuple(pipeline.feature_names_in_) == MODEL_FEATURES


def test_reproducibility():
    rows = [
        {
            "project_id": "P1",
            "relative_quality": 0.0,
            "heuristic_score": 0,
            "scenario_id": "1",
            "round_idx": 1,
            "parent_id": "X",
            "capacity_delta_mw": 0,
            "turbine_dispersion_stddev": 0,
            "parent_rank": 1,
            "mutation_type": "EDGE_RECONNECT",
        },
        {
            "project_id": "P1",
            "relative_quality": 1.0,
            "heuristic_score": 0,
            "scenario_id": "2",
            "round_idx": 1,
            "parent_id": "X",
            "capacity_delta_mw": 0,
            "turbine_dispersion_stddev": 0,
            "parent_rank": 1,
            "mutation_type": "EDGE_RECONNECT",
        },
        {
            "project_id": "P2",
            "relative_quality": 0.0,
            "heuristic_score": 0,
            "scenario_id": "3",
            "round_idx": 1,
            "parent_id": "X",
            "capacity_delta_mw": 0,
            "turbine_dispersion_stddev": 0,
            "parent_rank": 1,
            "mutation_type": "EDGE_RECONNECT",
        },
        {
            "project_id": "P2",
            "relative_quality": 1.0,
            "heuristic_score": 0,
            "scenario_id": "4",
            "round_idx": 1,
            "parent_id": "X",
            "capacity_delta_mw": 0,
            "turbine_dispersion_stddev": 0,
            "parent_rank": 1,
            "mutation_type": "EDGE_RECONNECT",
        },
    ]

    metrics1, macro1 = cross_validate_model("hist_gb", rows, 2, random_seed=123)
    metrics2, macro2 = cross_validate_model("hist_gb", rows, 2, random_seed=123)

    assert macro1 == macro2
    assert metrics1 == metrics2
