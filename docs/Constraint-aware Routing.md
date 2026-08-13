# Constraint-aware routing

The Python optimisation path accepts an optional `avoidance_geojson`
FeatureCollection. The field is additive: clients that omit it continue to use the
uniform base cost surface.

Each feature is projected into the project CRS and normalized into a typed
`ConstraintLayer`. The supported policy properties are:

| Property | Meaning |
| --- | --- |
| `constraint_id` | Stable feature identity. A deterministic positional ID is used when omitted. |
| `constraint_type` | `ROAD`, `HT_LINE`, `WATERCOURSE`, `PARCEL`, or `RESTRICTED_AREA`. |
| `routing_mode` | Optional explicit `SOFT_PENALTY` or `HARD_EXCLUSION`. |
| `buffer_m` | Optional per-feature metric buffer; otherwise `routing_config.avoidance_buffer_m` is used. |
| `cost_weight` | Optional positive finite soft-cost addition; otherwise `routing_config.avoidance_cost_weight` is used. It is invalid on a hard exclusion. |

When `routing_mode` is omitted, roads, HT lines, watercourses, and ordinary
parcels are soft penalties. Restricted areas and polygonal no-go features are hard
exclusions. An explicit mode always overrides the type default.

Hard exclusions rasterize to positive infinity and cannot be traversed by A*.
Soft constraints add finite traversal cost and may be crossed when the alternative
route is more expensive. Rasterization sorts layers by stable ID, does not mutate
the input surface, and produces the same result regardless of feature order.

Before scenario generation, every WTG and the selected substation are checked
against hard buffered geometry and the final blocked raster. A covered endpoint is
rejected with an input error. After refinement, the selected network is checked
again against the projected vector layers during presentation packaging.

When constraints are supplied, `recommended_result.spatial_constraint_summary`
reports:

- hard-exclusion violation count, which must be zero;
- soft-constraint intersection count and route overlap length;
- road-crossing count; and
- affected parcel count and route overlap length.

These are routing/compliance indicators, not construction approval or parcel
compensation estimates.

## V1 regression coverage

SURGE-PY-021 exercises this behavior through `POST /api/v1/optimise`, the
compatibility endpoint used by the Java integration. The committed API tests
adapt `optimisation-python/tests/fixtures/constraint_demo_project_v2.json` by
adding the required legacy `scenario` field, so V1 and V2 validate the same
deterministic Python-contract case.

The V1 regression suite proves that:

- the route crosses the soft road once, reports positive soft overlap, and is
  geometrically disjoint from the hard polygon;
- identical requests produce byte-identical response bodies;
- a WTG outside the raw `restricted-1` polygon but inside its hard buffer is
  rejected with HTTP 422 and an endpoint-specific error; and
- omitting `avoidance_geojson` leaves the constraint summary absent and retains
  the direct, uniform-cost route.

## Fixture provenance

`constraint_demo_project_v2.json` is hand-authored to exercise Python's request,
rasterization, validation, routing, and reporting contract. It is not a payload
captured from a KMZ upload/preview/commit cycle and does not verify Java's
KMZ-to-JSON transformation.

Using the repository fixture vocabulary, its provenance is `SYNTHETIC` and its
verification is `PYTHON_CONTRACT_VERIFIED`; it is not
`ROUND_TRIP_VERIFIED`. `REAL_SOURCE` and `DERIVED` are reserved for retained
source artifacts and documented transformations, respectively.

Upgrading it to a verified round-trip fixture requires a fixed test KMZ to pass
through the real frontend/Java workflow, followed by capture and comparison of
the exact request `OptimizationJobService` sends to Python. See the
[fixture provenance README](../optimisation-python/tests/fixtures/README.md) for
the ownership and evidence requirements.
