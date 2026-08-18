import hashlib
import json
import logging
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Protocol

import joblib
import pandas as pd
import sklearn

from app.optimisation.ml.feature_schema import (
    CATEGORICAL_FEATURES,
    MODEL_FEATURES,
    PRE_RANKER_FEATURE_SCHEMA_VERSION,
)
from app.optimisation.search_models import RankingModelConfig

logger = logging.getLogger(__name__)

_ARTIFACT_TYPE = "SURGE_CANDIDATE_PRE_RANKER"
_CORPUS_CONTRACT_VERSION = 1
_MODEL_VERSION = "1"
_MODEL_TARGET = "relative_quality"
_SUPPORTED_MODEL_TYPES = {"ridge", "hist_gb"}


class RankingModelInferenceError(Exception):
    """Raised when the ranking model fails to infer a score."""


@dataclass(frozen=True)
class MutationFeatureVector:
    """The authoritative PY-039/PY-040 pre-ranker feature row."""

    heuristic_score: float
    capacity_delta_mw: float
    turbine_dispersion_stddev: float
    parent_rank: float
    round_idx: int
    mutation_type: str

    def as_model_row(self) -> dict[str, object]:
        row = asdict(self)
        return {name: row[name] for name in MODEL_FEATURES}


class MutationRankingModel(Protocol):
    """Protocol for scoring candidate search mutations."""

    def score(self, feature: MutationFeatureVector) -> float: ...


@dataclass(frozen=True)
class HeuristicRankingModel:
    """Default fallback model that preserves deterministic heuristic ranking."""

    load_failed: bool = False

    def score(self, feature: MutationFeatureVector) -> float:
        return feature.heuristic_score


def _sha256(path: Path) -> str:
    hasher = hashlib.sha256()
    with path.open("rb") as model_file:
        while chunk := model_file.read(8192):
            hasher.update(chunk)
    return hasher.hexdigest()


def _require_metadata(metadata: object, key: str, expected: object) -> None:
    if not isinstance(metadata, dict) or metadata.get(key) != expected:
        actual = metadata.get(key) if isinstance(metadata, dict) else None
        raise ValueError(
            f"Incompatible artifact metadata {key}: expected {expected!r}, "
            f"got {actual!r}"
        )


def _validate_metadata(metadata: object, model_file: Path) -> None:
    _require_metadata(metadata, "artifact_type", _ARTIFACT_TYPE)
    _require_metadata(
        metadata, "feature_schema_version", PRE_RANKER_FEATURE_SCHEMA_VERSION
    )
    _require_metadata(metadata, "corpus_contract_version", _CORPUS_CONTRACT_VERSION)
    _require_metadata(metadata, "feature_names", list(MODEL_FEATURES))
    _require_metadata(metadata, "categorical_features", list(CATEGORICAL_FEATURES))
    _require_metadata(metadata, "target", _MODEL_TARGET)
    _require_metadata(metadata, "lower_score_is_better", True)

    if not isinstance(metadata, dict):
        raise ValueError("Artifact metadata must be a JSON object")
    _require_metadata(metadata, "model_version", _MODEL_VERSION)
    if metadata.get("model_type") not in _SUPPORTED_MODEL_TYPES:
        raise ValueError(
            f"Unsupported artifact model_type: {metadata.get('model_type')!r}"
        )
    _require_metadata(
        metadata,
        "library_versions",
        {"scikit-learn": sklearn.__version__, "pandas": pd.__version__},
    )

    expected_hash = metadata.get("model_sha256")
    actual_hash = _sha256(model_file)
    if not isinstance(expected_hash, str) or expected_hash != actual_hash:
        raise ValueError(
            "Artifact model_sha256 does not match model.joblib: "
            f"expected {expected_hash!r}, got {actual_hash!r}"
        )


class SklearnRankingModel:
    """Adapts a validated PY-039 sklearn artifact to runtime ranking."""

    def __init__(self, model_path: str):
        artifact_dir = Path(model_path)
        if not artifact_dir.is_dir():
            raise ValueError("model_path must reference a PY-039 artifact directory")

        model_file = artifact_dir / "model.joblib"
        metadata_file = artifact_dir / "metadata.json"
        if not model_file.is_file():
            raise ValueError(f"Artifact is missing {model_file.name}")
        if not metadata_file.is_file():
            raise ValueError(f"Artifact is missing {metadata_file.name}")

        with metadata_file.open(encoding="utf-8") as metadata_stream:
            metadata: Any = json.load(metadata_stream)
        _validate_metadata(metadata, model_file)

        self._model = joblib.load(model_file)
        if not hasattr(self._model, "predict"):
            raise ValueError(f"Loaded model from {model_file} lacks a predict method")
        actual_features = tuple(getattr(self._model, "feature_names_in_", ()))
        if actual_features != MODEL_FEATURES:
            raise ValueError(
                "Loaded model input features do not match artifact metadata: "
                f"expected {MODEL_FEATURES!r}, got {actual_features!r}"
            )

    def score(self, feature: MutationFeatureVector) -> float:
        frame = pd.DataFrame([feature.as_model_row()], columns=list(MODEL_FEATURES))
        try:
            result = self._model.predict(frame)
            return float(result[0])
        except Exception as exc:
            raise RankingModelInferenceError(f"Inference failed: {exc}") from exc


def load_ranking_model(config: RankingModelConfig) -> MutationRankingModel:
    """Load a validated artifact, recording when configured loading fails."""
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
        return HeuristicRankingModel(load_failed=True)
