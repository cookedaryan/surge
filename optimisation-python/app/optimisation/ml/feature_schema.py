PRE_RANKER_FEATURE_SCHEMA_VERSION = 1

NUMERIC_FEATURES = (
    "heuristic_score",
    "capacity_delta_mw",
    "turbine_dispersion_stddev",
    "parent_rank",
    "round_idx",
)

CATEGORICAL_FEATURES = ("mutation_type",)

COMPARISON_GROUP_COLUMNS = (
    "project_id",
    "round_idx",
    "parent_id",
)

MODEL_FEATURES = NUMERIC_FEATURES + CATEGORICAL_FEATURES
