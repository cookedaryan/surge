from collections import defaultdict
from typing import Any

import numpy as np
import scipy.stats

from .feature_schema import COMPARISON_GROUP_COLUMNS


def compute_group_metrics(
    group_rows: list[dict[str, Any]], k: int, score_key: str
) -> dict[str, float]:
    if k <= 0:
        raise ValueError("k must be strictly positive")
        
    n = len(group_rows)
    if n <= 1:
        return {
            "capture_at_k": 0.0,
            "top_k_recall": 0.0,
            "rank_correlation": 0.0,
            "valid": 0.0,
        }

    # Deterministic tie-breaking for predicted ordering:
    # 1. score_key ascending (or predicted_quality ascending)
    # 2. heuristic_score ascending
    # 3. scenario_id ascending

    def pred_sort_key(r: dict[str, Any]) -> tuple[Any, ...]:
        return (r[score_key], r["heuristic_score"], r["scenario_id"])

    predicted_ordered = sorted(group_rows, key=pred_sort_key)

    # Canonical ordering is already encoded in relative_quality ascending
    canonical_ordered = sorted(group_rows, key=lambda r: r["relative_quality"])

    actual_k = min(k, n)

    canonical_top_k_ids = {r["scenario_id"] for r in canonical_ordered[:actual_k]}
    predicted_top_k_ids = {r["scenario_id"] for r in predicted_ordered[:actual_k]}

    canonical_best_id = canonical_ordered[0]["scenario_id"]

    capture = 1.0 if canonical_best_id in predicted_top_k_ids else 0.0
    recall = len(canonical_top_k_ids.intersection(predicted_top_k_ids)) / actual_k

    # rank correlation
    canonical_ranks = {r["scenario_id"]: i for i, r in enumerate(canonical_ordered)}
    predicted_ranks = {r["scenario_id"]: i for i, r in enumerate(predicted_ordered)}

    x = [canonical_ranks[r["scenario_id"]] for r in group_rows]
    y = [predicted_ranks[r["scenario_id"]] for r in group_rows]

    corr, _ = scipy.stats.spearmanr(x, y)
    if np.isnan(corr):
        corr = 0.0

    return {
        "capture_at_k": capture,
        "top_k_recall": recall,
        "rank_correlation": float(corr),
        "valid": 1.0,
    }


def aggregate_project_metrics(
    rows: list[dict[str, Any]], score_key: str, k: int
) -> dict[str, float]:
    groups = defaultdict(list)
    for row in rows:
        key = tuple(row[col] for col in COMPARISON_GROUP_COLUMNS)
        groups[key].append(row)

    group_metrics = []
    for g_rows in groups.values():
        if len(g_rows) > 1:
            group_metrics.append(compute_group_metrics(g_rows, k, score_key))

    if not group_metrics:
        return {"capture_at_k": 0.0, "top_k_recall": 0.0, "rank_correlation": 0.0}

    return {
        "capture_at_k": float(np.mean([m["capture_at_k"] for m in group_metrics])),
        "top_k_recall": float(np.mean([m["top_k_recall"] for m in group_metrics])),
        "rank_correlation": float(np.mean([m["rank_correlation"] for m in group_metrics])),
    }


def macro_aggregate_metrics(
    project_metrics: dict[str, dict[str, float]],
) -> dict[str, float]:
    if not project_metrics:
        return {"capture_at_k": 0.0, "top_k_recall": 0.0, "rank_correlation": 0.0}

    n_proj = len(project_metrics)
    return {
        "capture_at_k": float(sum(pm["capture_at_k"] for pm in project_metrics.values()) / n_proj),
        "top_k_recall": float(sum(pm["top_k_recall"] for pm in project_metrics.values()) / n_proj),
        "rank_correlation": float(
            sum(pm["rank_correlation"] for pm in project_metrics.values()) / n_proj
        ),
    }


def evaluate_baseline(
    rows: list[dict[str, Any]], k: int
) -> tuple[dict[str, dict[str, float]], dict[str, float]]:
    # Baseline uses heuristic_score directly
    project_rows = defaultdict(list)
    for row in rows:
        project_rows[row["project_id"]].append(row)

    project_metrics = {}
    for pid, p_rows in project_rows.items():
        project_metrics[pid] = aggregate_project_metrics(p_rows, "heuristic_score", k)

    macro = macro_aggregate_metrics(project_metrics)
    return project_metrics, macro
