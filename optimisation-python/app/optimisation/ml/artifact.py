import hashlib
import json
import logging
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

import joblib
from sklearn.pipeline import Pipeline


@dataclass
class ValidationSummary:
    projects: int
    rows: int
    comparison_groups: int
    usable_ranking_rows: int
    metrics: dict[str, Any]


@dataclass
class ArtifactMetadata:
    artifact_type: str
    model_version: str
    feature_schema_version: int
    corpus_contract_version: int
    model_type: str
    feature_names: list[str]
    categorical_features: list[str]
    target: str
    lower_score_is_better: bool
    training_row_count: int
    training_project_count: int
    comparison_group_count: int
    random_seed: int
    canonical_corpus_sha256: str
    model_sha256: str
    library_versions: dict[str, str]
    model_parameters: dict[str, Any]
    feature_profile: dict[str, Any]
    validation_summary: ValidationSummary


def save_artifact(
    pipeline: Pipeline,
    metadata: ArtifactMetadata,
    validation_report: dict[str, Any],
    output_dir: Path,
) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)

    # Save model
    model_path = output_dir / "model.joblib"
    joblib.dump(pipeline, model_path)

    # Hash model
    hasher = hashlib.sha256()
    with open(model_path, "rb") as f:
        while chunk := f.read(8192):
            hasher.update(chunk)

    metadata.model_sha256 = hasher.hexdigest()

    # Save metadata
    with open(output_dir / "metadata.json", "w", encoding="utf-8") as f:
        json.dump(asdict(metadata), f, indent=2)

    # Save report
    with open(output_dir / "validation_report.json", "w", encoding="utf-8") as f:
        json.dump(validation_report, f, indent=2)

    # Write status file
    with open(output_dir / "STATUS", "w", encoding="utf-8") as f:
        f.write("OFFLINE_VALIDATED\n")

    logging.info(f"Saved artifact to {output_dir} (Status: OFFLINE_VALIDATED)")


def load_artifact(output_dir: Path) -> Pipeline:
    model_path = output_dir / "model.joblib"
    return joblib.load(model_path)
