def test_compute_group_metrics_capture_and_recall():
    import pytest

    from app.optimisation.ml.validation import compute_group_metrics

    group = [
        {
            "scenario_id": "S1",
            "relative_quality": 0.0,
            "predicted_quality": 0.8,
            "heuristic_score": 0,
        },
        {
            "scenario_id": "S2",
            "relative_quality": 0.2,
            "predicted_quality": 0.1,
            "heuristic_score": 0,
        },
        {
            "scenario_id": "S3",
            "relative_quality": 0.5,
            "predicted_quality": 0.2,
            "heuristic_score": 0,
        },
        {
            "scenario_id": "S4",
            "relative_quality": 1.0,
            "predicted_quality": 0.9,
            "heuristic_score": 0,
        },
    ]

    metrics = compute_group_metrics(group, k=2, score_key="predicted_quality")

    assert metrics["capture_at_k"] == 0.0
    assert metrics["top_k_recall"] == 0.5

    with pytest.raises(ValueError):
        compute_group_metrics(group, k=0, score_key="predicted_quality")
