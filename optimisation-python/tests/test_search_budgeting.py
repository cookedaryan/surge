"""Tests for deterministic search budgeting and termination."""

import pytest

from app.optimisation.search_models import CandidateSearchConfig


def test_search_config_validation() -> None:
    # Valid config
    config = CandidateSearchConfig(
        enabled=True,
        max_search_evaluations=10,
        max_candidate_proposals=50,
    )
    assert config.max_search_evaluations == 10
    assert config.max_candidate_proposals == 50

    with pytest.raises(ValueError):
        CandidateSearchConfig(max_search_evaluations=-1)

    with pytest.raises(ValueError):
        CandidateSearchConfig(max_candidate_proposals=-1)

    # Boolean should fail
    with pytest.raises(ValueError):
        CandidateSearchConfig(max_search_evaluations=True)
