def test_feature_schema_matches_py038():
    from app.optimisation.ml.feature_schema import (
        CATEGORICAL_FEATURES,
        NUMERIC_FEATURES,
        PRE_RANKER_FEATURE_SCHEMA_VERSION,
    )

    assert PRE_RANKER_FEATURE_SCHEMA_VERSION == 1
    assert "heuristic_score" in NUMERIC_FEATURES
    assert "mutation_type" in CATEGORICAL_FEATURES
