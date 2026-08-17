import json
from pathlib import Path

from app.optimisation.ml.artifact import (
    ArtifactMetadata,
    ValidationSummary,
    save_artifact,
)
from app.optimisation.ml.training import build_pipeline


def test_save_artifact(tmp_path: Path):
    pipe = build_pipeline("ridge", 42)
    val_sum = ValidationSummary(1, 2, 3, 4, {})
    meta = ArtifactMetadata(
        "T",
        "1",
        1,
        1,
        "ridge",
        [],
        [],
        "t",
        True,
        1,
        1,
        1,
        1,
        "sha",
        "",
        {},
        {},
        val_sum,
    )

    save_artifact(pipe, meta, {}, tmp_path)

    assert (tmp_path / "model.joblib").exists()
    assert (tmp_path / "metadata.json").exists()
    assert (tmp_path / "validation_report.json").exists()
    assert (tmp_path / "STATUS").exists()

    with open(tmp_path / "STATUS") as f:
        assert f.read().strip() == "OFFLINE_VALIDATED"

    with open(tmp_path / "metadata.json") as f:
        data = json.load(f)
        assert data["model_sha256"] != ""
