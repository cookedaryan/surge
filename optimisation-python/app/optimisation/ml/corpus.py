import csv
import hashlib
import math
from pathlib import Path
from typing import Any, NamedTuple

from .feature_schema import COMPARISON_GROUP_COLUMNS, MODEL_FEATURES


class TrainingCorpus(NamedTuple):
    rows: list[dict[str, Any]]
    fingerprint: str


def load_training_corpus(path: Path) -> TrainingCorpus:
    with open(path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        if not reader.fieldnames:
            raise ValueError("Corpus has no columns")

        required_cols = set(COMPARISON_GROUP_COLUMNS) | set(MODEL_FEATURES) | {
            "evaluation.rank",
            "total_route_length_m",
            "feasible",
            "scenario_id",
        }

        missing = required_cols - set(reader.fieldnames)
        if missing:
            raise ValueError(f"Missing required columns: {missing}")

        raw_rows = list(reader)

    if not raw_rows:
        raise ValueError("Corpus is empty")

    processed_rows = []
    project_ids = set()
    groups: dict[tuple[Any, ...], list[dict[str, Any]]] = {}

    for i, row in enumerate(raw_rows):
        if not row["project_id"].strip():
            raise ValueError(f"Row {i} has empty project_id")
        project_ids.add(row["project_id"])

        if not row["feasible"].strip() in ("True", "False"):
            raise ValueError(f"Row {i} has invalid feasible value: {row['feasible']}")

        is_feasible = row["feasible"] == "True"

        for num_feat in [
            "heuristic_score",
            "capacity_delta_mw",
            "turbine_dispersion_stddev",
            "parent_rank",
        ]:
            try:
                val = float(row[num_feat])
                if math.isnan(val) or math.isinf(val):
                    raise ValueError(f"Row {i} has NaN/inf in {num_feat}")
                row[num_feat] = val
            except ValueError as e:
                raise ValueError(
                    f"Row {i} has non-numeric {num_feat}: {row[num_feat]}"
                ) from e

        row["round_idx"] = int(row["round_idx"])

        if is_feasible:
            if not row.get("evaluation.rank") or not row["evaluation.rank"].strip():
                raise ValueError(f"Row {i} is feasible but missing rank")
            row["evaluation.rank"] = int(row["evaluation.rank"])

            cost_col = (
                "evaluation.lifecycle_cost"
                if "evaluation.lifecycle_cost" in row
                else "lifecycle_cost"
            )
            if not row.get(cost_col) or not row[cost_col].strip():
                raise ValueError(f"Row {i} is feasible but missing cost")
            row["lifecycle_cost"] = float(row[cost_col])

            row["total_route_length_m"] = float(row["total_route_length_m"])
        else:
            row["evaluation.rank"] = None
            row["lifecycle_cost"] = None
            if not row["total_route_length_m"].strip():
                row["total_route_length_m"] = None
            else:
                row["total_route_length_m"] = float(row["total_route_length_m"])

        group_key = tuple(row[col] for col in COMPARISON_GROUP_COLUMNS)
        groups.setdefault(group_key, []).append(row)

        processed_rows.append(row)

    if len(project_ids) < 2:
        raise ValueError("Corpus must contain at least two distinct projects")

    if not any(len(g) > 1 for g in groups.values()):
        raise ValueError(
            "Corpus must contain at least one comparison group with >1 candidate"
        )

    fingerprint = _canonical_fingerprint(processed_rows)
    return TrainingCorpus(rows=processed_rows, fingerprint=fingerprint)


def _canonical_fingerprint(rows: list[dict[str, Any]]) -> str:
    sorted_rows = sorted(
        rows,
        key=lambda r: (
            r["project_id"],
            r["round_idx"],
            r["parent_id"],
            r["scenario_id"],
        ),
    )

    all_keys = sorted(list(sorted_rows[0].keys()))

    hasher = hashlib.sha256()
    for row in sorted_rows:
        row_str = "|".join(f"{k}:{row[k]}" for k in all_keys)
        hasher.update(row_str.encode("utf-8"))
        hasher.update(b"\n")

    return hasher.hexdigest()
