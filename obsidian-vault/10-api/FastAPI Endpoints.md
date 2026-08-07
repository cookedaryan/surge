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
    "features": []
  },
  "metrics": {
    "feeder_count": 0,
    "total_length_m": 0.0,
    "estimated_cost": null,
    "message": "Optimisation pipeline stub initialized"
  }
}
```

#### Field Details
- `request_id`: Echoes correlation ID from request.
- `status`: `"success"` or `"failed"`.
- `scenario`: Selected optimization scenario.
- `feeder_routes_geojson`: RFC 7946 GeoJSON FeatureCollection containing generated routes.
- `metrics`: Typed `OptimisationMetrics` object with non-negative constraints.
