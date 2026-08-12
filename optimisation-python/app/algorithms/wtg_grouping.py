import math
from dataclasses import dataclass
from decimal import Decimal
from enum import StrEnum

import numpy as np
from scipy.optimize import Bounds, LinearConstraint, milp
from shapely.geometry import Point
from sklearn.cluster import KMeans

from app.models.spatial import ProjectSpatialData


class GroupingObjective(StrEnum):
    """Controls the feeder-assignment objective used during WTG grouping.

    MINIMIZE_DISTANCE
        Default. Minimise sum of squared turbine-to-centroid distances.
        Produces spatially compact feeders.

    BALANCE_WTG_COUNT
        Replace the distance-squared MILP objective with an objective that
        minimises the maximum deviation from the ideal equal-split WTG count
        per feeder.  The centroids supplied by KMeans are still used to seed
        the initial cluster count, but the objective function is changed.
    """

    MINIMIZE_DISTANCE = "minimize_distance"
    BALANCE_WTG_COUNT = "balance_wtg_count"


@dataclass(frozen=True)
class FeederAssignment:
    feeder_id: str
    turbine_ids: tuple[str, ...]
    total_capacity_mw: float
    centroid: Point


@dataclass(frozen=True)
class FeederGroupingResult:
    feeder_count: int
    assignments: tuple[FeederAssignment, ...]


def group_wtgs(
    project: ProjectSpatialData,
    feeder_capacity_mw: float,
    *,
    random_state: int = 42,
    objective: GroupingObjective = GroupingObjective.MINIMIZE_DISTANCE,
) -> FeederGroupingResult:
    """
    Deterministically groups wind turbines into feeders such that no feeder
    exceeds `feeder_capacity_mw`. Uses spatial clustering (K-Means) mapped to a
    strictly mathematically bounded Mixed-Integer Linear Program (MILP) to find the
    absolute minimum number of feeders required without exceeding capacities.

    Parameters
    ----------
    project:
        Spatial data containing turbine locations and capacities.
    feeder_capacity_mw:
        Maximum electrical capacity per feeder (MW).
    random_state:
        Seed for the KMeans initialisation.  Default 42 preserves the
        historic baseline behaviour.  Changing this seed produces different
        MILP centroid seeds and therefore a different (but still valid)
        feeder grouping.  Must be a non-negative integer.
    objective:
        Controls what the MILP optimises.  ``MINIMIZE_DISTANCE`` (default)
        minimises squared turbine-to-centroid distance, producing spatially
        compact feeders.  ``BALANCE_WTG_COUNT`` minimises the maximum
        deviation from the ideal equal-split WTG count per feeder.
    """
    if not math.isfinite(feeder_capacity_mw) or feeder_capacity_mw <= 0:
        raise ValueError("feeder_capacity_mw must be positive and finite")

    turbines = project.turbines
    if not turbines:
        return FeederGroupingResult(feeder_count=0, assignments=())

    # Sort turbines deterministically for input-order invariance
    sorted_wtgs = sorted(
        turbines, key=lambda w: (w.location.x, w.location.y, w.turbine_id)
    )

    capacities_kw = []
    coords = []
    turbine_ids = []

    try:
        dec_feeder = Decimal(str(feeder_capacity_mw))
        if (dec_feeder * 1000) % 1 != 0:
            raise ValueError(
                f"feeder_capacity_mw ({feeder_capacity_mw}) "
                f"has more than 3 decimal places"
            )
        feeder_capacity_kw = int(dec_feeder * 1000)
    except Exception as e:
        raise ValueError(f"Invalid feeder_capacity_mw: {e}") from e

    if feeder_capacity_kw <= 0:
        raise ValueError("feeder_capacity_mw must be positive and >= 0.001 MW")

    for wtg in sorted_wtgs:
        if (
            wtg.capacity_mw is None
            or wtg.capacity_mw <= 0
            or not math.isfinite(wtg.capacity_mw)
        ):
            raise ValueError(
                f"Turbine {wtg.turbine_id} has invalid capacity: {wtg.capacity_mw}"
            )

        try:
            dec_cap = Decimal(str(wtg.capacity_mw))
            if (dec_cap * 1000) % 1 != 0:
                raise ValueError(
                    f"Turbine {wtg.turbine_id} capacity ({wtg.capacity_mw}) "
                    f"has more than 3 decimal places"
                )
            cap_kw = int(dec_cap * 1000)
        except Exception as e:
            raise ValueError(f"Invalid capacity for {wtg.turbine_id}: {e}") from e

        if cap_kw <= 0:
            raise ValueError(f"Turbine {wtg.turbine_id} capacity must be >= 0.001 MW")

        if cap_kw > feeder_capacity_kw:
            raise ValueError(
                f"Turbine {wtg.turbine_id} capacity ({wtg.capacity_mw}) "
                f"exceeds feeder max ({feeder_capacity_mw})"
            )

        capacities_kw.append(cap_kw)
        coords.append((wtg.location.x, wtg.location.y))
        turbine_ids.append(wtg.turbine_id)

    num_wtgs = len(sorted_wtgs)
    total_kw = sum(capacities_kw)

    base_k = math.ceil(total_kw / feeder_capacity_kw)
    if base_k <= 0:
        base_k = 1

    best_assignments: list[int] = list(range(num_wtgs))  # fallback

    for k in range(base_k, num_wtgs + 1):
        if k == 1:
            best_assignments = [0] * num_wtgs
            break

        if k == num_wtgs:
            best_assignments = list(range(num_wtgs))
            break

        # Determine number of distinct points
        unique_coords = set(coords)
        if len(unique_coords) < k:
            # Cannot run K-Means with fewer unique points than K.
            # We must map them directly or let it just fallback to N bins.
            # We can still solve the MILP without K-means seeds (or with dummy seeds).
            seeds = coords[:k]  # just pick first k
        else:
            # Generate K-Means spatial seeds for MILP objective
            kmeans = KMeans(n_clusters=k, random_state=random_state, n_init="auto")
            kmeans.fit(coords)
            seeds = kmeans.cluster_centers_.tolist()

        if objective == GroupingObjective.BALANCE_WTG_COUNT:
            assignments = _solve_milp_balance(
                coords, capacities_kw, k, feeder_capacity_kw
            )
        else:
            assignments = _solve_milp_assignment(
                coords, capacities_kw, seeds, k, feeder_capacity_kw
            )
        if assignments is not None:
            # Defensive invariant check
            if any(a == -1 for a in assignments):
                raise RuntimeError("MILP success but not all turbines assigned")

            feeder_sums = [0] * k
            for i, c_idx in enumerate(assignments):
                feeder_sums[c_idx] += capacities_kw[i]

            for s in feeder_sums:
                if s > feeder_capacity_kw:
                    raise RuntimeError("MILP success but capacity exceeded!")

            best_assignments = assignments
            break

    # Build final groupings
    clusters: dict[int, list[int]] = {}
    for idx, c_id in enumerate(best_assignments):
        clusters.setdefault(c_id, []).append(idx)

    raw_assignments = []
    for _c_id, node_indices in clusters.items():
        if not node_indices:
            continue

        t_ids = tuple(turbine_ids[i] for i in node_indices)
        cap_sum = sum(capacities_kw[i] for i in node_indices) / 1000.0

        cx = sum(coords[i][0] for i in node_indices) / len(node_indices)
        cy = sum(coords[i][1] for i in node_indices) / len(node_indices)

        raw_assignments.append((cx, cy, t_ids, cap_sum))

    # Sort by centroid (x, then y) and turbine IDs for stable feeder ID assignment
    raw_assignments.sort(key=lambda r: (r[0], r[1], r[2]))

    feeder_assignments = []
    for idx, (cx, cy, t_ids, cap_sum) in enumerate(raw_assignments):
        feeder_assignments.append(
            FeederAssignment(
                feeder_id=f"F{idx + 1}",
                turbine_ids=t_ids,
                total_capacity_mw=cap_sum,
                centroid=Point(cx, cy),
            )
        )

    return FeederGroupingResult(
        feeder_count=len(feeder_assignments),
        assignments=tuple(feeder_assignments),
    )


def _solve_milp_assignment(
    coords: list[tuple[float, float]],
    capacities_kw: list[int],
    centroids: list[tuple[float, float]],
    k: int,
    feeder_capacity_kw: int,
) -> list[int] | None:
    """
    Uses scipy.optimize.milp to solve the capacitated assignment problem.
    Variables: x_ij (binary) = 1 if turbine i is in feeder j.
    Total variables: N * k.
    Index mapping: var_idx = i * k + j.
    """
    n = len(coords)
    num_vars = n * k

    # 1. Objective function: Minimize sum(d_ij^2 * x_ij)
    c = np.zeros(num_vars)
    for i in range(n):
        for j in range(k):
            # Distance squared
            dx = coords[i][0] - centroids[j][0]
            dy = coords[i][1] - centroids[j][1]
            dist_sq = dx**2 + dy**2
            c[i * k + j] = dist_sq

    # 2. Constraints

    # Constraint A: Each turbine assigned to exactly one feeder
    # sum_j(x_ij) == 1
    # n constraints
    a_eq = np.zeros((n, num_vars))
    b_eq = np.ones(n)
    for i in range(n):
        for j in range(k):
            a_eq[i, i * k + j] = 1.0

    # Constraint B: Capacity of each feeder <= feeder_capacity_kw
    # sum_i(P_i * x_ij) <= C_max
    # k constraints
    a_ub = np.zeros((k, num_vars))
    b_ub = np.full(k, feeder_capacity_kw)
    for j in range(k):
        for i in range(n):
            a_ub[j, i * k + j] = capacities_kw[i]

    # Combine equality and inequality constraints
    # scipy milp takes LinearConstraint(A, lb, ub)
    # For a_eq == 1: lb = 1, ub = 1
    # For a_ub <= C_max: lb = -inf, ub = C_max

    a_matrix = np.vstack((a_eq, a_ub))
    lb = np.concatenate((b_eq, np.full(k, -np.inf)))
    ub = np.concatenate((b_eq, b_ub))

    constraints = LinearConstraint(a_matrix, lb, ub)

    # Bounds: all variables must be binary (0 <= x <= 1)
    bounds = Bounds(0, 1)
    integrality = np.ones(num_vars)  # 1 means integer

    res = milp(
        c=c,
        constraints=constraints,
        integrality=integrality,
        bounds=bounds,
        options={"disp": False},
    )

    if res.success:
        assignments = [-1] * n
        x_sol = np.round(res.x).astype(int)
        for i in range(n):
            for j in range(k):
                if x_sol[i * k + j] == 1:
                    assignments[i] = j
                    break
        return assignments

    return None


def _solve_milp_balance(
    coords: list[tuple[float, float]],
    capacities_kw: list[int],
    k: int,
    feeder_capacity_kw: int,
) -> list[int] | None:
    """Solve the capacitated assignment problem with an explicit balance objective.

    The objective minimises the maximum absolute deviation of feeder WTG count
    from the ideal equal split (n / k), subject to:

    - Each turbine assigned to exactly one feeder.
    - No feeder exceeds ``feeder_capacity_kw``.

    Variables
    ---------
    x_ij (binary)
        1 if turbine i belongs to feeder j.  Index: ``i * k + j``.
    t (continuous, >= 0)
        Upper-bound auxiliary variable representing the maximum feeder WTG-count
        deviation from the ideal.  Minimising t drives all feeders toward equal
        WTG counts.

    Total variables: n * k + 1.
    """
    n = len(coords)
    if n == 0 or k == 0:
        return None

    ideal = n / k  # ideal WTGs per feeder (may be fractional)
    num_x = n * k
    num_vars = num_x + 1  # last variable = t

    # --- Objective: minimise t -------------------------------------------
    c = np.zeros(num_vars)
    c[-1] = 1.0  # t

    # --- Constraint A: each turbine assigned to exactly one feeder ---------
    # sum_j x_ij == 1  for i in range(n)
    a_eq = np.zeros((n, num_vars))
    b_eq = np.ones(n)
    for i in range(n):
        for j in range(k):
            a_eq[i, i * k + j] = 1.0

    # --- Constraint B: feeder capacity <= feeder_capacity_kw --------------
    # sum_i P_i * x_ij <= C  for j in range(k)
    a_cap = np.zeros((k, num_vars))
    b_cap = np.full(k, float(feeder_capacity_kw))
    for j in range(k):
        for i in range(n):
            a_cap[j, i * k + j] = capacities_kw[i]

    # --- Constraint C: balance upper bound --------------------------------
    # sum_i x_ij - ideal <= t   ↔   sum_i x_ij - t <= ideal
    # For j in range(k)
    a_ub_pos = np.zeros((k, num_vars))
    b_ub_pos = np.full(k, ideal)
    for j in range(k):
        for i in range(n):
            a_ub_pos[j, i * k + j] = 1.0
        a_ub_pos[j, -1] = -1.0  # -t

    # --- Constraint D: balance lower bound --------------------------------
    # ideal - sum_i x_ij <= t   ↔   -sum_i x_ij - t <= -ideal
    a_ub_neg = np.zeros((k, num_vars))
    b_ub_neg = np.full(k, -ideal)
    for j in range(k):
        for i in range(n):
            a_ub_neg[j, i * k + j] = -1.0
        a_ub_neg[j, -1] = -1.0  # -t

    # --- Combine into a single LinearConstraint ---------------------------
    # Equality: lb == ub == 1 for rows 0..n-1
    # Inequality (<=): lb == -inf for capacity and balance rows
    a_matrix = np.vstack((a_eq, a_cap, a_ub_pos, a_ub_neg))
    lb = np.concatenate(
        (b_eq, np.full(k, -np.inf), np.full(k, -np.inf), np.full(k, -np.inf))
    )
    ub = np.concatenate((b_eq, b_cap, b_ub_pos, b_ub_neg))

    constraints = LinearConstraint(a_matrix, lb, ub)

    # x_ij are binary; t is continuous non-negative
    bounds = Bounds(
        lb=np.zeros(num_vars),
        ub=np.concatenate((np.ones(num_x), [float(n)])),
    )
    integrality = np.concatenate((np.ones(num_x), [0.0]))  # t is continuous

    res = milp(
        c=c,
        constraints=constraints,
        integrality=integrality,
        bounds=bounds,
        options={"disp": False},
    )

    if res.success:
        assignments = [-1] * n
        x_sol = np.round(res.x[:num_x]).astype(int)
        for i in range(n):
            for j in range(k):
                if x_sol[i * k + j] == 1:
                    assignments[i] = j
                    break
        return assignments

    return None
