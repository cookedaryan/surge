import numpy as np

from app.optimisation.ml.training import build_pipeline, cross_validate_model


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
            "heuristic_score": 0,
            "scenario_id": "1",
            "round_idx": 1,
            "parent_id": "X",
        },
        {
            "project_id": "P1",
            "relative_quality": 1.0,
            "heuristic_score": 0,
            "scenario_id": "2",
            "round_idx": 1,
            "parent_id": "X",
        },
        {
            "project_id": "P2",
            "relative_quality": 0.0,
            "heuristic_score": 0,
            "scenario_id": "3",
            "round_idx": 1,
            "parent_id": "X",
        },
        {
            "project_id": "P2",
            "relative_quality": 1.0,
            "heuristic_score": 0,
            "scenario_id": "4",
            "round_idx": 1,
            "parent_id": "X",
        },
        {
            "project_id": "P3",
            "relative_quality": 0.0,
            "heuristic_score": 0,
            "scenario_id": "5",
            "round_idx": 1,
            "parent_id": "X",
        },
        {
            "project_id": "P3",
            "relative_quality": 1.0,
            "heuristic_score": 0,
            "scenario_id": "6",
            "round_idx": 1,
            "parent_id": "X",
        },
    ]

    calls = []

    class DummyEstimator:
        def fit(self, x, y):
            calls.append(("fit", set(x["project_id"])))

        def predict(self, x):
            calls.append(("predict", set(x["project_id"])))
            return np.zeros(len(x))

    class DummyPipeline:
        def fit(self, x, y):
            calls.append(("fit", set(x["project_id"])))

        def predict(self, x):
            calls.append(("predict", set(x["project_id"])))
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
