# WTG Grouping and Capacity-Constrained Assignment

> [!success] Implementation status: Implemented
> `app/algorithms/wtg_grouping.py` groups projected WTGs and reports the feeder count. The public API does not yet expose individual assignments.

## What Is a Feeder Group?

A feeder group is a set of wind turbine generators assigned to the same collector feeder. Grouping is an electrical-capacity and topology preparation step: it decides which turbines belong together before a route or feeder tree is constructed.

The current constraint is expressed in active power:

$$
\sum_{i \in F_j} P_i \leq P_{\text{feeder,max}}
$$

This is a planning approximation in MW, not a conductor ampacity calculation. Current, voltage, power factor, thermal rating, and voltage drop will require the future electrical-analysis stage.

## Current Algorithm

1. Validate a positive finite feeder limit.
2. Sort WTGs by projected x, y, and ID for input-order independence.
3. Convert MW values to integer kW using `Decimal`; capacities may have at most three decimal places.
4. Calculate the lower bound `ceil(total_kW / feeder_capacity_kW)`.
5. Try feeder counts from that bound up to the number of WTGs.
6. For each count, use deterministic K-Means (`random_state=42`) to generate spatial seed centroids.
7. Solve a binary mixed-integer linear program (MILP) assigning every WTG to exactly one seed while respecting feeder capacity.
8. Minimize the sum of squared projected distance from WTGs to their assigned seed.
9. Sort resulting centroids and assign stable identifiers `F1`, `F2`, and so on.

## Why Combine K-Means and MILP?

K-Means encourages geographically compact groups but does not enforce feeder capacity. The MILP provides hard assignment and capacity constraints. K-Means supplies the locations used by the MILP distance objective; it is not trusted to produce the final grouping by itself.

The approach selects the first feasible feeder count, so it prioritizes the minimum number of feeders and then spatial compactness for the chosen seeds. It does not globally optimize the centroids and assignments together.

## Output

`FeederGroupingResult` contains:

- `feeder_count`
- immutable `FeederAssignment` values
- stable feeder ID
- assigned turbine IDs
- total MW
- projected centroid Point

Only `feeder_count` currently enters `OptimisationMetrics`; assignments must later feed the feeder-topology stage and/or become part of the API response.

## Edge Cases

- Missing, non-finite, or non-positive WTG capacity is rejected.
- A WTG larger than the feeder limit is rejected.
- Coincident WTGs are handled without requiring unique K-Means points.
- An empty internal project returns zero groups, although API preprocessing currently rejects an empty WTG collection earlier.

## Related Notes

- [[Feeder Planning]]
- [[Routing]]
- [[Geospatial Integrity & CRS]]
- [[FastAPI Endpoints|FastAPI Microservice Specification]]
