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
          "edge": "substation:SUB-001-wtg:WTG-001"
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
    "message": "Pipeline initialized. Projected into WGS 84 / UTM zone 43N"
  }
}
```

#### Field Details
- `request_id`: Echoes correlation ID from request.
- `status`: `"success"` or `"failed"`.
- `scenario`: Selected optimization scenario.
- `feeder_routes_geojson`: RFC 7946 FeatureCollection containing one two-point WGS84 LineString per selected MST edge. These features expose preliminary topology, not cost-surface routes.
- `metrics.feeder_count`: Number of capacity-constrained feeder assignments.
- `metrics.total_length_m`: Sum of all per-feeder routed edge distances in the selected projected CRS. This is the cost-surface-aware routed line length over the base uniform raster.
- `metrics.estimated_cost`: Currently `null`; the lifecycle cost function is not implemented.
- `metrics.message`: Pipeline status and selected projected CRS. The exact UTM zone depends on input coordinates.

### Current Pipeline Semantics

A `success` response means Point preprocessing, candidate-graph construction, WTG grouping, per-feeder MST construction, and WGS84 serialization completed. It does not mean that A*, obstacle avoidance, cost-surface routing, pole placement, ROW analysis, electrical validation, or lifecycle cost has completed.

Each Feature represents an A* routed segment rather than an entire feeder route. The property is named `feederName`, which Java's route importer recognizes. Java will persist each feature as a distinct record, meaning one feeder produces multiple feeder-summary segment rows until aggregation is implemented.

See [[Per-Feeder MST Topology]] for the MST algorithm and its assumptions.
