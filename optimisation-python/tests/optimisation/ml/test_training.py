from app.optimisation.ml.training import build_pipeline


def test_pipeline_construction():
    pipe = build_pipeline("ridge", 42)
    assert pipe.named_steps["preprocessor"]
    assert pipe.named_steps["estimator"].__class__.__name__ == "Ridge"

    pipe2 = build_pipeline("hist_gb", 42)
    assert (
        pipe2.named_steps["estimator"].__class__.__name__
        == "HistGradientBoostingRegressor"
    )
