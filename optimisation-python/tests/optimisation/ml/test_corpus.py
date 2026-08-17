import pytest

from app.optimisation.ml.corpus import _canonical_fingerprint


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
