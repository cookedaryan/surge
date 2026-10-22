from app.optimisation.ml.targets import build_relative_targets


def test_build_relative_targets_semantics():
    rows = [
        {
            "project_id": "P1",
            "round_idx": 1,
            "parent_id": "P-1",
            "scenario_id": "S1",
            "feasible": "True",
            "evaluation.rank": 2,
            "lifecycle_cost": 100,
            "total_route_length_m": 10,
        },
        {
            "project_id": "P1",
            "round_idx": 1,
            "parent_id": "P-1",
            "scenario_id": "S2",
            "feasible": "True",
            "evaluation.rank": 1,
            "lifecycle_cost": 100,
            "total_route_length_m": 10,
        },
        {
            "project_id": "P1",
            "round_idx": 1,
            "parent_id": "P-1",
            "scenario_id": "S3",
            "feasible": "False",
            "evaluation.rank": None,
            "lifecycle_cost": None,
            "total_route_length_m": None,
        },
    ]

    usable, report = build_relative_targets(rows)

    assert len(usable) == 3
    # S2 rank 1 -> best (0.0)
    # S1 rank 2 -> next (0.5)
    # S3 infeasible -> worst (1.0)

    s2 = next(r for r in usable if r["scenario_id"] == "S2")
    s1 = next(r for r in usable if r["scenario_id"] == "S1")
    s3 = next(r for r in usable if r["scenario_id"] == "S3")

    assert s2["relative_quality"] == 0.0
    assert s1["relative_quality"] == 0.5
    assert s3["relative_quality"] == 1.0


def test_singleton_group_excluded():
    rows = [
        {
            "project_id": "P1",
            "round_idx": 1,
            "parent_id": "P-1",
            "scenario_id": "S1",
            "feasible": "True",
            "evaluation.rank": 1,
            "lifecycle_cost": 100,
            "total_route_length_m": 10,
        },
    ]
    usable, report = build_relative_targets(rows)
    assert len(usable) == 0
    assert report["singleton_group_count"] == 1
