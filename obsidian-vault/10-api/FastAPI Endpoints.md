# FastAPI Microservice Specification

## Service Boundary

The Python service exposes two synchronous endpoints under `/api/v1`. Spring Boot is the intended caller; browsers should use the Java API rather than call Python directly.

In development, Swagger UI is available at `/docs`, ReDoc at `/redoc`, and OpenAPI JSON at `/api/v1/openapi.json`. These routes are disabled when `ENVIRONMENT=production`.

| Method | Endpoint | Purpose |
| --- | --- | --- |
| `GET` | `/api/v1/health` | Process-level health response |
| `POST` | `/api/v1/optimise` | Validate project points, build a candidate graph, and group WTGs |

## Health Endpoint

`GET /api/v1/health` returns HTTP 200:

```json
{
  "status": "healthy",
  "service": "surge-python-gis"
}
```

This confirms that the FastAPI process can answer a request. It does not check PostGIS, Java connectivity, scientific solver readiness, or downstream dependencies.

## Optimize Endpoint

`POST /api/v1/optimise` accepts `application/json` and returns `OptimisationResponse`.

### Request

```json
{
  "request_id": "job-4d3c",
  "project_id": "project-123",
  "scenario": "Balanced",
  "wtg_geojson": {
    "type": "FeatureCollection",
    "features": [
      {
        "type": "Feature",
        "geometry": {"type": "Point", "coordinates": [77.2302, 28.6301]},
        "properties": {"id": "WTG-001", "capacity_mw": 3.0}
      }
    ]
  },
  "substation_geojson": {
    "type": "FeatureCollection",
    "features": [
      {
        "type": "Feature",
        "geometry": {"type": "Point", "coordinates": [77.2090, 28.6139]},
        "properties": {"id": "SUB-001"}
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

### Top-level validation

- `request_id`: required non-empty string; Java derives it from the job ID.
- `project_id`: required non-empty string. Python echoes no project data and does not query the database.
- `scenario`: exactly one of `Minimum Cost`, `Minimum Land Impact`, `Minimum Environmental Impact`, or `Balanced`.
- `electrical_params`: optional object; omitted fields use the defaults shown above.
- `feeder_capacity_mw`: greater than zero; the grouping implementation supports at most three decimal places.
- `max_voltage_drop_pct`: greater than zero and at most 100. It is validated but not yet used in an electrical calculation.
- `row_width_m`: greater than zero. It is validated but not yet used to create a corridor.

### GeoJSON validation

- Each input can be a Feature or FeatureCollection.
- WTG input must contain at least one Point; substation input must contain exactly one Point.
- Coordinates must be finite WGS84 longitude/latitude values.
- Each feature needs a non-empty unique identifier. WTGs accept `properties.id` or `properties.turbine_id`; the substation accepts `properties.id` or `properties.substation_id`.
- Every WTG must provide a positive finite `properties.capacity_mw` for the current grouping pipeline.
- A WTG capacity may not exceed `feeder_capacity_mw`.
- Substation capacity is optional and is not currently enforced against total generation.

### Current response

For the one-WTG example above, the response shape is:

```json
{
  "request_id": "job-4d3c",
  "status": "success",
  "scenario": "Balanced",
  "feeder_routes_geojson": {
    "type": "FeatureCollection",
    "features": []
  },
  "metrics": {
    "feeder_count": 1,
    "total_length_m": 0.0,
    "estimated_cost": null,
    "message": "Pipeline initialized. Projected into WGS 84 / UTM zone 43N"
  }
}
```

The exact UTM name depends on input location. A `success` response currently means preprocessing, graph construction, and grouping completed; it does not mean routes, costs, or electrical results were calculated.

### Error behavior

Schema validation and expected domain validation both return HTTP 422. Pydantic errors use FastAPI's structured validation list. Preprocessing/grouping errors use:

```json
{"detail": "WTG FeatureCollection is empty"}
```

Unexpected errors follow FastAPI's server-error behavior. The service does not currently define a typed failure response body even though the response model permits `status: "failed"`; expected validation failures are HTTP errors rather than successful `failed` responses.

## Related Notes

- [[Python Engine]]
- [[Overview & Layout]]
- [[Geospatial Integrity & CRS]]
- [[WTG Grouping]]
