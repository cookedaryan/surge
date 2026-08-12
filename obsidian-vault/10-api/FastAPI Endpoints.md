# FastAPI Microservice Specification

The Python optimization microservice exposes RESTful endpoints prefixed with `/api/v1`.

## Endpoints Summary

| Method | Endpoint | Description |
| --- | --- | --- |
| `GET` | `/api/v1/health` | Health check endpoint returning status and service name |
| `POST` | `/api/v1/optimise` | Runs SURGE route optimization pipeline |

---

## 1. Health Check Endpoint

- **URL**: `/api/v1/health`
- **Method**: `GET`
- **Response**: `200 OK`
```json
{
  "status": "healthy",
  "service": "surge-python-gis"
}
```

---

## 2. Route Optimisation Endpoint

- **URL**: `/api/v1/optimise`
- **Method**: `POST`
- **Content-Type**: `application/json`

### Request Schema (`OptimisationRequest`)

```json
{
  "request_id": "req-987654",
  "project_id": "proj-123456",
  "scenario": "Balanced",
  "wtg_geojson": {
    "type": "FeatureCollection",
    "features": [
      {
        "type": "Feature",
        "geometry": { "type": "Point", "coordinates": [77.2302, 28.6301] },
        "properties": { "id": "WTG-001", "capacity_mw": 3.0 }
      }
    ]
  },
  "substation_geojson": {
    "type": "FeatureCollection",
    "features": [
      {
        "type": "Feature",
        "geometry": { "type": "Point", "coordinates": [77.2090, 28.6139] },
        "properties": { "id": "SUB-001" }
      }
    ]
  },
  "electrical_params": {
    "feeder_capacity_mw": 20.0,
    "max_voltage_drop_pct": 5.0,
    "row_width_m": 18.0
  }
}
```

#### Field Validation Rules
- `request_id`: Required string (min length 1). Used to correlate requests across Java Spring Boot and Python logs.
- `project_id`: Required string (min length 1).
- `scenario`: Literal string - one of `"Minimum Cost"`, `"Minimum Land Impact"`, `"Minimum Environmental Impact"`, `"Balanced"`.
- `electrical_params`:
  - `feeder_capacity_mw`: float > 0 (default: `20.0`)
  - `max_voltage_drop_pct`: float > 0 and <= 100 (default: `5.0`)
  - `row_width_m`: float > 0 (default: `18.0`)

---

### Response Schema (`OptimisationResponse`)

```json
{
  "request_id": "req-987654",
  "status": "success",
  "scenario": "Balanced",
  "feeder_routes_geojson": {
    "type": "FeatureCollection",
    "features": [
      {
        "type": "Feature",
        "properties": {
          "feederName": "F1",
          "edge": "substation:SUB-001-wtg:WTG-001",
          "length_m": 2738.4,
          "traversal_cost": 2738.4,
          "original_length_m": 2743.1,
          "refined_length_m": 2738.4,
          "original_traversal_cost": 2743.1,
          "refined_traversal_cost": 2738.4
        },
        "geometry": {
          "type": "LineString",
          "coordinates": [
            [77.209, 28.6139],
            [77.2302, 28.6301]
          ]
        }
      }
    ]
  },
  "metrics": {
    "feeder_count": 1,
    "total_length_m": 2743.0606898885517,
    "estimated_cost": null,
    "message": "Pipeline completed. Refined routes over the uniform cost surface. Projected into WGS 84 / UTM zone 43N"
  }
}
```

#### Field Details
- `request_id`: Echoes correlation ID from request.
- `status`: `"success"` or `"failed"`.
- `scenario`: Selected optimization scenario.
- `feeder_routes_geojson`: RFC 7946 FeatureCollection containing one refined WGS84 LineString per selected MST edge.
- `length_m` / `traversal_cost`: Compatibility properties containing the refined measurements.
- `original_length_m` / `original_traversal_cost`: Measurements retained from the raw A* route.
- `refined_length_m` / `refined_traversal_cost`: Measurements recalculated from the refined geometry. Refined cost integrates physical length through each crossed raster cell.
- `metrics.feeder_count`: Number of capacity-constrained feeder assignments.
- `metrics.total_length_m`: Sum of all per-feeder routed edge distances in the selected projected CRS. This is the cost-surface-aware routed line length over the base uniform raster.
- `metrics.estimated_cost`: Currently `null`; the lifecycle cost function is not implemented.
- `metrics.message`: Pipeline status and selected projected CRS. The exact UTM zone depends on input coordinates.

### Current Pipeline Semantics

A `success` response means Point preprocessing, candidate-graph construction, WTG grouping, per-feeder MST construction, A* routing, cost-preserving route refinement, and WGS84 serialization completed. The current cost surface is uniform, so success does not mean terrain, restriction, pole, ROW, electrical, or lifecycle-cost analysis has completed.

Each Feature represents an A* routed segment rather than an entire feeder route. The property is named `feederName`, which Java's route importer recognizes. Java will persist each feature as a distinct record, meaning one feeder produces multiple feeder-summary segment rows until aggregation is implemented.

Spatial infeasibility is returned as HTTP 422. This includes blocked or out-of-bounds endpoints, no available path, CRS/cost-surface validation failures, and coincident route endpoints that cannot form a non-degenerate refined LineString.

### SURGE-PY-020 compatibility rule

The richer MVP result will continue to use `POST /api/v1/optimise`. Because the
Java backend already consumes this response, PY-020 must retain
`request_id`, `status`, `scenario`, `feeder_routes_geojson`, and `metrics`.
Legacy route and metric fields will describe the recommended candidate. New
candidate-comparison, recommendation, electrical-summary, and map-ready result
fields are additive. Raw project-boundary and restriction-layer ingestion is
not part of the frozen MVP API scope. See [[Surge MVP Ticket Plan]].

See [[Per-Feeder MST Topology]] for the MST algorithm and its assumptions.
