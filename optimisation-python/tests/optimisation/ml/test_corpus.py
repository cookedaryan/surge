import csv

import pytest

from app.optimisation.ml.corpus import _canonical_fingerprint, load_training_corpus


def test_canonical_fingerprint_is_stable():
    rows1 = [
        {
            "project_id": "P1",
            "round_idx": 1,
            "parent_id": "P-1",
            "scenario_id": "S1",
            "val": 1,
        },
        {
            "project_id": "P1",
            "round_idx": 1,
            "parent_id": "P-1",
            "scenario_id": "S2",
            "val": 2,
        },
    ]
    rows2 = [
        {
            "project_id": "P1",
            "round_idx": 1,
            "parent_id": "P-1",
            "scenario_id": "S2",
            "val": 2,
        },
        {
            "project_id": "P1",
            "round_idx": 1,
            "parent_id": "P-1",
            "scenario_id": "S1",
            "val": 1,
        },
    ]
    assert _canonical_fingerprint(rows1) == _canonical_fingerprint(rows2)


def _write_corpus(rows, tmp_path):
    p = tmp_path / "test.csv"
    with open(p, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)
    return p


def _valid_row(overrides=None):
    r = {
        "project_id": "P1",
        "round_idx": "1",
        "parent_id": "P-1",
        "scenario_id": "S1",
        "feasible": "True",
        "evaluation.rank": "1",
        "lifecycle_cost": "100",
        "total_route_length_m": "10",
        "mutation_type": "EDGE_RECONNECT",
        "heuristic_score": "1.0",
        "capacity_delta_mw": "0.0",
        "turbine_dispersion_stddev": "0.0",
        "parent_rank": "1.0",
    }
    if overrides:
        r.update(overrides)
    return r


def _valid_corpus():
    return [
        _valid_row({"scenario_id": "S1", "project_id": "P1"}),
        _valid_row({"scenario_id": "S2", "project_id": "P1"}),
        _valid_row({"scenario_id": "S3", "project_id": "P2"}),
        _valid_row({"scenario_id": "S4", "project_id": "P2"}),
    ]


def test_corpus_blank_parent_id(tmp_path):
    rows = _valid_corpus()
    rows[0]["parent_id"] = ""
    with pytest.raises(ValueError, match="empty parent_id"):
        load_training_corpus(_write_corpus(rows, tmp_path))


def test_corpus_invalid_mutation(tmp_path):
    rows = _valid_corpus()
    rows[0]["mutation_type"] = "INVALID_MUT"
    with pytest.raises(ValueError, match="invalid mutation_type"):
        load_training_corpus(_write_corpus(rows, tmp_path))


def test_corpus_nan_inf_labels(tmp_path):
    rows = _valid_corpus()
    rows[0]["lifecycle_cost"] = "NaN"
    with pytest.raises(ValueError, match="invalid lifecycle_cost"):
        load_training_corpus(_write_corpus(rows, tmp_path))


def test_corpus_duplicate_scenario(tmp_path):
    rows = _valid_corpus()
    rows[1]["scenario_id"] = "S1"
    with pytest.raises(ValueError, match="Duplicate scenario_id"):
        load_training_corpus(_write_corpus(rows, tmp_path))


def test_corpus_requires_two_projects_with_usable_comparison_groups(tmp_path):
    rows = _valid_corpus()
    rows[3]["parent_id"] = "P-2"

    with pytest.raises(
        ValueError,
        match="at least two projects with usable comparison groups",
    ):
        load_training_corpus(_write_corpus(rows, tmp_path))
