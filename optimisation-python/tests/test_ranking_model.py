import json
from pathlib import Path

import pandas as pd
import pytest
import sklearn

from app.optimisation.ml.artifact import (
    ArtifactMetadata,
    ValidationSummary,
    save_artifact,
)
from app.optimisation.ml.feature_schema import (
    CATEGORICAL_FEATURES,
    MODEL_FEATURES,
    PRE_RANKER_FEATURE_SCHEMA_VERSION,
)
from app.optimisation.ml.training import build_pipeline
from app.optimisation.ranking_model import (
    HeuristicRankingModel,
    MutationFeatureVector,
    RankingModelInferenceError,
    SklearnRankingModel,
    load_ranking_model,
)
from app.optimisation.search_models import RankingModelConfig


def _feature(heuristic_score: float = 10.0) -> MutationFeatureVector:
    return MutationFeatureVector(
        heuristic_score=heuristic_score,
        capacity_delta_mw=2.0,
        turbine_dispersion_stddev=3.0,
        parent_rank=1.0,
        round_idx=1,
        mutation_type="FEEDER_REASSIGNMENT",
    )


@pytest.fixture
def ranking_artifact(tmp_path: Path) -> Path:
    rows = [
        {
            "heuristic_score": float(index),
            "capacity_delta_mw": float(index % 3),
            "turbine_dispersion_stddev": float(index * 2),
            "parent_rank": float(index % 2 + 1),
            "round_idx": index % 2 + 1,
            "mutation_type": (
                "FEEDER_REASSIGNMENT" if index % 2 else "EDGE_RECONNECT"
            ),
        }
        for index in range(1, 9)
    ]
    pipeline = build_pipeline("ridge", 42)
    targets = [r["heuristic_score"] / 10 for r in rows]
    pipeline.fit(pd.DataFrame(rows, columns=list(MODEL_FEATURES)), targets)
    metadata = ArtifactMetadata(
        artifact_type="SURGE_CANDIDATE_PRE_RANKER",
        model_version="1",
        feature_schema_version=PRE_RANKER_FEATURE_SCHEMA_VERSION,
        corpus_contract_version=1,
        model_type="ridge",
        feature_names=list(MODEL_FEATURES),
        categorical_features=list(CATEGORICAL_FEATURES),
        target="relative_quality",
        lower_score_is_better=True,
        training_row_count=len(rows),
        training_project_count=2,
        comparison_group_count=2,
        random_seed=42,
        canonical_corpus_sha256="test-corpus",
        model_sha256="",
        library_versions={
            "scikit-learn": sklearn.__version__,
            "pandas": pd.__version__,
        },
        model_parameters={},
        feature_profile={},
        validation_summary=ValidationSummary(2, len(rows), 2, len(rows), {}),
    )
    save_artifact(pipeline, metadata, {}, tmp_path)
    return tmp_path


def test_heuristic_ranking_model_parity() -> None:
    assert HeuristicRankingModel().score(_feature(42.5)) == 42.5


def test_py039_pipeline_round_trip_supports_runtime_feature_row(
    ranking_artifact: Path,
) -> None:
    model = SklearnRankingModel(str(ranking_artifact))

    low_score = model.score(_feature(1.0))
    high_score = model.score(_feature(8.0))

    assert low_score < high_score


def test_load_ranking_model_success(ranking_artifact: Path) -> None:
    config = RankingModelConfig(enabled=True, model_path=str(ranking_artifact))
    model = load_ranking_model(config)

    assert isinstance(model, SklearnRankingModel)


def test_direct_joblib_path_fails_closed(ranking_artifact: Path) -> None:
    config = RankingModelConfig(
        enabled=True, model_path=str(ranking_artifact / "model.joblib")
    )

    model = load_ranking_model(config)

    assert isinstance(model, HeuristicRankingModel)
    assert model.load_failed is True


def test_missing_model_records_load_fallback(tmp_path: Path) -> None:
    config = RankingModelConfig(enabled=True, model_path=str(tmp_path / "missing"))

    model = load_ranking_model(config)

    assert isinstance(model, HeuristicRankingModel)
    assert model.load_failed is True


def test_metadata_contract_mismatch_falls_back(
    ranking_artifact: Path,
) -> None:
    metadata_path = ranking_artifact / "metadata.json"
    metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
    metadata["feature_names"] = list(reversed(metadata["feature_names"]))
    metadata_path.write_text(json.dumps(metadata), encoding="utf-8")

    model = load_ranking_model(
        RankingModelConfig(enabled=True, model_path=str(ranking_artifact))
    )

    assert isinstance(model, HeuristicRankingModel)
    assert model.load_failed is True


def test_model_hash_mismatch_falls_back(ranking_artifact: Path) -> None:
    metadata_path = ranking_artifact / "metadata.json"
    metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
    metadata["model_sha256"] = "0" * 64
    metadata_path.write_text(json.dumps(metadata), encoding="utf-8")

    model = load_ranking_model(
        RankingModelConfig(enabled=True, model_path=str(ranking_artifact))
    )

    assert isinstance(model, HeuristicRankingModel)
    assert model.load_failed is True


def test_inference_failure(
    ranking_artifact: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    model = SklearnRankingModel(str(ranking_artifact))

    def mock_predict(*args: object, **kwargs: object) -> None:
        raise ValueError("Simulated inference error")

    monkeypatch.setattr(model._model, "predict", mock_predict)

    with pytest.raises(RankingModelInferenceError):
        model.score(_feature())
