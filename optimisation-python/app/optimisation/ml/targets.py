from typing import Any

from .feature_schema import COMPARISON_GROUP_COLUMNS


def build_relative_targets(
    rows: list[dict[str, Any]],
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    # Group rows
    groups: dict[tuple[Any, ...], list[dict[str, Any]]] = {}
    for row in rows:
        _key = tuple(row[col] for col in COMPARISON_GROUP_COLUMNS)
        groups.setdefault(_key, []).append(row)

    usable_rows = []
    singleton_group_count = 0
    singleton_row_count = 0

    for _key, group in groups.items():
        if len(group) == 1:
            singleton_group_count += 1
            singleton_row_count += 1
            continue

        def sort_key(r: dict[str, Any]) -> tuple[Any, ...]:
            # 1. Eligible candidates first (feasible == 'True' / True)
            # 2. canonical evaluation.rank ascending
            # 3. lifecycle_cost ascending
            # 4. total_route_length_m ascending
            # 5. child_id ascending
            is_infeasible = str(r["feasible"]) != "True"
            rank = r.get("evaluation.rank")
            cost = r.get("lifecycle_cost")
            length = r.get("total_route_length_m")

            # Handle None values for infeasible
            safe_rank = float("inf") if rank is None else rank
            safe_cost = float("inf") if cost is None else cost
            safe_length = float("inf") if length is None else length

            return (is_infeasible, safe_rank, safe_cost, safe_length, r["scenario_id"])

        sorted_group = sorted(group, key=sort_key)
        n = len(sorted_group)

        for i, row in enumerate(sorted_group):
            row["relative_quality"] = i / (n - 1)
            usable_rows.append(row)

    report = {
        "singleton_group_count": singleton_group_count,
        "singleton_row_count": singleton_row_count,
        "usable_ranking_rows": len(usable_rows),
        "total_comparison_groups": len(groups),
    }

    return usable_rows, report
