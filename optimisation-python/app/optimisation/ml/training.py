from typing import Any

import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import HistGradientBoostingRegressor
from sklearn.linear_model import Ridge
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler

from .feature_schema import CATEGORICAL_FEATURES, NUMERIC_FEATURES
from .validation import aggregate_project_metrics, macro_aggregate_metrics


def build_pipeline(model_name: str, random_seed: int = 42) -> Pipeline:
    preprocessor = ColumnTransformer(
        transformers=[
            ("num", StandardScaler(), list(NUMERIC_FEATURES)),
            ("cat", OneHotEncoder(handle_unknown="ignore"), list(CATEGORICAL_FEATURES)),
        ]
    )

    if model_name == "ridge":
        estimator = Ridge(random_state=random_seed)
    elif model_name == "hist_gb":
        estimator = HistGradientBoostingRegressor(
            random_state=random_seed, early_stopping=False
        )
    else:
        raise ValueError(f"Unknown model: {model_name}")

    return Pipeline([("preprocessor", preprocessor), ("estimator", estimator)])


def cross_validate_model(
    model_name: str, rows: list[dict[str, Any]], k: int, random_seed: int = 42
) -> tuple[dict[str, dict[str, float]], dict[str, float]]:
    project_ids = sorted({r["project_id"] for r in rows})
    project_metrics = {}

    for test_proj in project_ids:
        train_rows = [r for r in rows if r["project_id"] != test_proj]
        test_rows = [r for r in rows if r["project_id"] == test_proj]

        if not train_rows or not test_rows:
            continue

        pipeline = build_pipeline(model_name, random_seed)

        x_train = pd.DataFrame(train_rows)
        y_train = [r["relative_quality"] for r in train_rows]

        pipeline.fit(x_train, y_train)

        x_test = pd.DataFrame(test_rows)
        preds = pipeline.predict(x_test)

        # Inject predictions back for validation
        test_rows_with_preds = []
        for row, pred in zip(test_rows, preds, strict=False):
            r2 = dict(row)
            r2["predicted_quality"] = pred
            test_rows_with_preds.append(r2)

        project_metrics[test_proj] = aggregate_project_metrics(
            test_rows_with_preds, "predicted_quality", k
        )

    macro = macro_aggregate_metrics(project_metrics)
    return project_metrics, macro


def train_final_model(
    model_name: str, rows: list[dict[str, Any]], random_seed: int = 42
) -> Pipeline:
    pipeline = build_pipeline(model_name, random_seed)
    x_train = pd.DataFrame(rows)
    y_train = [r["relative_quality"] for r in rows]
    pipeline.fit(x_train, y_train)
    return pipeline


def select_best_model(results: dict[str, dict[str, float]]) -> str:
    # Primary: top_k_recall
    # Secondary: capture_at_k, rank_correlation
    # Tie: simpler model (ridge over hist_gb)

    best_model = None
    best_score = -1.0

    # Priority for tie-breaking: ridge is simpler than hist_gb
    model_priority = {"ridge": 1, "hist_gb": 2}

    for name, metrics in results.items():
        score = metrics["top_k_recall"]

        if best_model is None:
            best_model = name
            best_score = score
        elif score > best_score + 1e-6:
            best_model = name
            best_score = score
        elif abs(score - best_score) <= 1e-6:
            # Secondary check
            if metrics["capture_at_k"] > results[best_model]["capture_at_k"] + 1e-6:
                best_model = name
            elif (
                abs(metrics["capture_at_k"] - results[best_model]["capture_at_k"])
                <= 1e-6
            ):
                if (
                    metrics["rank_correlation"]
                    > results[best_model]["rank_correlation"] + 1e-6
                ):
                    best_model = name
                elif (
                    abs(
                        metrics["rank_correlation"]
                        - results[best_model]["rank_correlation"]
                    )
                    <= 1e-6
                ):
                    if model_priority[name] < model_priority[best_model]:
                        best_model = name

    return best_model or "ridge"
