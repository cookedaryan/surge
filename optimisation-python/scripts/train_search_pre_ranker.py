import argparse
import logging
import sys
from pathlib import Path

import pandas as pd
import sklearn

COMPONENT_DIR = Path(__file__).resolve().parent.parent
if str(COMPONENT_DIR) not in sys.path:
    sys.path.insert(0, str(COMPONENT_DIR))

from app.optimisation.ml.artifact import (  # noqa: E402
    ArtifactMetadata,
    ValidationSummary,
    save_artifact,
)
from app.optimisation.ml.corpus import load_training_corpus  # noqa: E402
from app.optimisation.ml.feature_schema import (  # noqa: E402
    CATEGORICAL_FEATURES,
    MODEL_FEATURES,
    PRE_RANKER_FEATURE_SCHEMA_VERSION,
)
from app.optimisation.ml.targets import build_relative_targets  # noqa: E402
from app.optimisation.ml.training import (  # noqa: E402
    cross_validate_model,
    select_best_model,
    train_final_model,
)
from app.optimisation.ml.validation import evaluate_baseline  # noqa: E402

logging.basicConfig(level=logging.INFO)


def main() -> None:
    parser = argparse.ArgumentParser(description="Train SURGE pre-ranker")
    parser.add_argument(
        "--corpus", type=Path, required=True, help="Path to search_corpus.csv"
    )
    parser.add_argument(
        "--output", type=Path, required=True, help="Output directory for artifact"
    )
    parser.add_argument("--k", type=int, default=5, help="Top-K for evaluation")
    parser.add_argument("--seed", type=int, default=42, help="Random seed")

    args = parser.parse_args()

    logging.info(f"Loading corpus from {args.corpus}")
    try:
        corpus = load_training_corpus(args.corpus)
    except Exception as e:
        logging.error(f"Failed to load corpus: {e}")
        sys.exit(1)

    logging.info(
        f"Loaded {len(corpus.rows)} valid rows. "
        f"Canonical fingerprint: {corpus.fingerprint}"
    )

    usable_rows, target_report = build_relative_targets(corpus.rows)
    logging.info(f"Target report: {target_report}")

    if len(usable_rows) == 0:
        logging.error("No usable ranking rows found.")
        sys.exit(1)

    # Validation
    logging.info("Evaluating baseline (heuristic_score)...")
    base_proj, base_macro = evaluate_baseline(usable_rows, args.k)

    results = {}
    reports = {}

    for model_name in ["ridge", "hist_gb"]:
        logging.info(f"Cross-validating {model_name}...")
        proj_metrics, macro_metrics = cross_validate_model(
            model_name, usable_rows, args.k, args.seed
        )
        results[model_name] = macro_metrics
        reports[model_name] = {
            "project_metrics": proj_metrics,
            "macro_metrics": macro_metrics,
        }

    # Select best
    best_model_name = select_best_model(results)
    logging.info(
        f"Selected best model: {best_model_name} based on Top-K Recall (macro-by-project)"
    )

    # Train final
    logging.info("Training final pipeline on all data...")
    final_pipeline = train_final_model(best_model_name, usable_rows, args.seed)

    # Validate Serialization Round-Trip
    logging.info("Validating serialization round-trip...")
    test_x = pd.DataFrame(usable_rows[:10])
    preds_before = final_pipeline.predict(test_x)

    import tempfile
    import joblib
    import os

    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_path = os.path.join(tmpdir, "model.joblib")
        joblib.dump(final_pipeline, tmp_path)
        reloaded = joblib.load(tmp_path)
        preds_after = reloaded.predict(test_x)

    import numpy as np

    if not np.allclose(preds_before, preds_after):
        logging.error("Serialization round-trip failed predictions check.")
        sys.exit(1)

    # Artifact
    logging.info(f"Saving artifact to {args.output}")

    val_summary = ValidationSummary(
        projects=len({r["project_id"] for r in usable_rows}),
        rows=len(corpus.rows),
        comparison_groups=target_report["total_comparison_groups"],
        usable_ranking_rows=len(usable_rows),
        metrics={
            "heuristic": base_macro,
            **{m: reports[m]["macro_metrics"] for m in ["ridge", "hist_gb"]},
        },
    )

    metadata = ArtifactMetadata(
        artifact_type="SURGE_CANDIDATE_PRE_RANKER",
        model_version="1",
        feature_schema_version=PRE_RANKER_FEATURE_SCHEMA_VERSION,
        corpus_contract_version=1,
        model_type=best_model_name,
        feature_names=list(MODEL_FEATURES),
        categorical_features=list(CATEGORICAL_FEATURES),
        target="relative_quality",
        lower_score_is_better=True,
        training_row_count=len(usable_rows),
        training_project_count=val_summary.projects,
        comparison_group_count=target_report["total_comparison_groups"]
        - target_report["singleton_group_count"],
        random_seed=args.seed,
        canonical_corpus_sha256=corpus.fingerprint,
        model_sha256="",  # Filled by save
        library_versions={
            "scikit-learn": sklearn.__version__,
            "pandas": pd.__version__,
        },
        model_parameters=final_pipeline.named_steps["estimator"].get_params(),
        validation_summary=val_summary,
    )

    full_report = {
        "corpus": target_report,
        "baseline": {"project": base_proj, "macro": base_macro},
        "models": reports,
        "selected_model": best_model_name,
    }

    save_artifact(final_pipeline, metadata, full_report, args.output)

    # Console summary
    print("\nSURGE ML PRE-RANKER TRAINING\n")
    print("Corpus\n------")
    print(f"Projects:             {val_summary.projects}")
    print(f"Rows:                {val_summary.rows}")
    print(f"Comparison groups:    {val_summary.comparison_groups}")
    print(f"Usable ranking rows: {val_summary.usable_ranking_rows}\n")
    print("Cross-validation\n----------------")
    print("Existing heuristic:")
    print(f"  Top-{args.k} recall:       {base_macro['top_k_recall']:.4f}")
    print(f"  Capture@{args.k}:          {base_macro['capture_at_k']:.4f}\n")

    for m in ["ridge", "hist_gb"]:
        print(f"{m}:")
        print(f"  Top-{args.k} recall:       {results[m]['top_k_recall']:.4f}")
        print(f"  Capture@{args.k}:          {results[m]['capture_at_k']:.4f}\n")

    print(f"Selected model:\n  {best_model_name}\n")
    print("Status:\nOFFLINE_VALIDATED")


if __name__ == "__main__":
    main()
