import json
import logging
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

import joblib

from app.models.spatial import WindTurbine
from app.optimisation.search_models import (
    EdgeReconnectMutation,
    FeederReassignmentMutation,
    FeederSwapMutation,
    RankingModelConfig,
    SearchMutation,
)

logger = logging.getLogger(__name__)


class RankingModelInferenceError(Exception):
    """Raised when the ranking model fails to infer a score."""

    pass


@dataclass(frozen=True)
class MutationFeatureVector:
    """Features extracted from a search mutation for ranking pre-evaluation."""

    schema_version: str
    mutation_type: str
    edge_weight: float
    parent_rank: float
    search_round: int
    capacity_delta_mw: float | None
    affected_feeder_dispersion_m: float | None


class MutationRankingModel(Protocol):
    """Protocol for scoring candidate search mutations."""

    def score(self, feature: MutationFeatureVector) -> float: ...


class HeuristicRankingModel:
    """Default fallback model that preserves current deterministic behavior."""

    def score(self, feature: MutationFeatureVector) -> float:
        return feature.edge_weight


class SklearnRankingModel:
    """Adapts a joblib-loaded scikit-learn regressor to the scoring protocol."""

    # Fixed ordering to ensure deterministic array construction
    _MUTATION_TYPE_ORDER = ("EDGE_RECONNECT", "FEEDER_REASSIGNMENT", "FEEDER_SWAP")

    def __init__(self, model_path: str):
        path = Path(model_path)
        if path.is_file() and path.suffix == ".joblib":
            model_file = path
        else:
            model_file = path / "model.joblib"
            metadata_file = path / "metadata.json"
            if metadata_file.exists():
                with open(metadata_file, "r", encoding="utf-8") as f:
                    metadata = json.load(f)
                
                # Dynamic import to avoid circular dependencies
                from app.optimisation.ml.feature_schema import PRE_RANKER_FEATURE_SCHEMA_VERSION
                
                version = metadata.get("feature_schema_version")
                if version is not None and version != PRE_RANKER_FEATURE_SCHEMA_VERSION:
                    raise ValueError(
                        f"Incompatible feature schema version: expected "
                        f"{PRE_RANKER_FEATURE_SCHEMA_VERSION}, got {version}"
                    )
        
        self._model = joblib.load(model_file)
        if not hasattr(self._model, "predict"):
            raise ValueError(f"Loaded model from {model_file} lacks a predict method")

    def score(self, feature: MutationFeatureVector) -> float:
        try:
            mut_type_idx = self._MUTATION_TYPE_ORDER.index(feature.mutation_type)
        except ValueError:
            mut_type_idx = -1

        features = [
            mut_type_idx,
            feature.edge_weight,
            feature.parent_rank,
            feature.search_round,
            feature.capacity_delta_mw if feature.capacity_delta_mw is not None else 0.0,
            (
                feature.affected_feeder_dispersion_m
                if feature.affected_feeder_dispersion_m is not None
                else 0.0
            ),
        ]

        try:
            res = self._model.predict([features])
            return float(res[0])
        except Exception as exc:
            raise RankingModelInferenceError(f"Inference failed: {exc}") from exc


def load_ranking_model(config: RankingModelConfig) -> MutationRankingModel:
    """Loads a ranking model from config, falling back to heuristic on failure."""
    if not config.enabled or config.model_path is None:
        return HeuristicRankingModel()

    try:
        return SklearnRankingModel(config.model_path)
    except Exception as exc:
        logger.warning(
            "Failed to load ranking model %s: %s, falling back to heuristic",
            config.model_path,
            exc,
        )
        return HeuristicRankingModel()


def build_feature_vector(
    mutation: SearchMutation,
    weight: float,
    parent_rank: float,
    round_idx: int,
    schema_version: str,
    turbines_by_id: Mapping[str, WindTurbine],
) -> MutationFeatureVector:
    """Constructs a MutationFeatureVector from cheap pre-evaluation data."""
    capacity_delta_mw: float | None = None
    affected_feeder_dispersion_m: float | None = None

    if isinstance(mutation, FeederReassignmentMutation):
        capacity_delta_mw = turbines_by_id[mutation.wtg_id].capacity_mw or 0.0
    elif isinstance(mutation, FeederSwapMutation):
        u_cap = turbines_by_id[mutation.wtg_id_1].capacity_mw or 0.0
        v_cap = turbines_by_id[mutation.wtg_id_2].capacity_mw or 0.0
        capacity_delta_mw = abs(u_cap - v_cap)
    elif isinstance(mutation, EdgeReconnectMutation):
        # Do not invent a value for EDGE_RECONNECT
        capacity_delta_mw = None

    return MutationFeatureVector(
        schema_version=schema_version,
        mutation_type=mutation.operator,
        edge_weight=weight,
        parent_rank=parent_rank,
        search_round=round_idx + 1,
        capacity_delta_mw=capacity_delta_mw,
        affected_feeder_dispersion_m=affected_feeder_dispersion_m,
    )
