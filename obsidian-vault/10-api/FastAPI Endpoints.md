# FastAPI Microservice Specification

> [!success] Implementation Status: Implemented
> The Python optimization engine (`optimisation-python`) exposes stateless REST endpoints under `/api/v1` and `/api/v2`. The service is consumed primarily by the Java Spring Boot backend for geospatial routing, capacity-constrained grouping, physical pole placement, Pandapower AC power flow, multi-objective ranking, and lifecycle cost calculations.

---

## Endpoints Overview

| Method | Endpoint | Purpose | API Contract Style |
| :--- | :--- | :--- | :--- |
| `GET` | `/api/v1/health` | Service liveness probe | JSON status response |
| `POST` | `/api/v1/optimise` | Legacy & Spring Boot compatible optimization endpoint | Additive wrapper with legacy GeoJSON + `recommended_result` |
| `POST` | `/api/v2/optimise` | Explicit engineering & multi-candidate optimization endpoint | Strict typed inputs: cable catalog, pole config, scoring weights, TCO |

---

## 1. Health Check Endpoint

### `GET /api/v1/health`
Checks whether the FastAPI application and Python scientific stack are operational.

#### Response (`200 OK`)
```json
{
  "status": "healthy",
  "service": "surge-python-gis"
}
```

---

## 2. Compatible Optimization Endpoint (`/api/v1/optimise`)

Consumed by Java Spring Boot `PythonOptimizationClient`. It accepts basic project GeoJSON and electrical parameters, executes the complete deterministic orchestrator, and returns both backward-compatible route collections and rich presentation models.

- **URL**: `/api/v1/optimise`
- **Method**: `POST`
- **Content-Type**: `application/json`

### Request Schema (`OptimisationRequest`)

```json
{
  "request_id": "req-8921-prod",
  "project_id": "93b1d1e4-6b22-47ec-a4b5-128214227f42",
  "scenario": "Balanced",
  "wtg_geojson": {
    "type": "FeatureCollection",
    "features": [
      {
        "type": "Feature",
        "geometry": { "type": "Point", "coordinates": [77.2302, 28.6301] },
        "properties": { "id": "WTG-001", "capacity_mw": 3.0 }
      },
      {
        "type": "Feature",
        "geometry": { "type": "Point", "coordinates": [77.2415, 28.6385] },
        "properties": { "id": "WTG-002", "capacity_mw": 3.0 }
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
  "avoidance_geojson": {
    "type": "FeatureCollection",
    "features": [
      {
        "type": "Feature",
        "geometry": {
          "type": "LineString",
          "coordinates": [[77.2150, 28.6200], [77.2250, 28.6250]]
        },
        "properties": {
          "feature_type": "ROAD",
          "cost_weight": 20.0
        }
      },
      {
        "type": "Feature",
        "geometry": {
          "type": "Polygon",
          "coordinates": [[[77.2200, 28.6200], [77.2250, 28.6200], [77.2250, 28.6250], [77.2200, 28.6250], [77.2200, 28.6200]]]
        },
        "properties": {
          "feature_type": "RESTRICTED_AREA",
          "buffer_m": 25.0
        }
      }
    ]
  },
  "electrical_params": {
    "feeder_capacity_mw": 20.0,
    "max_voltage_drop_pct": 5.0,
    "row_width_m": 18.0,
    "nominal_voltage_kv": 33.0
  },
  "routing_config": {
    "resolution_m": 10.0,
    "padding_m": 100.0,
    "avoidance_buffer_m": 10.0,
    "avoidance_cost_weight": 20.0,
    "row_width_m": 18.0
  },
  "pole_config": {
    "target_span_m": 100.0,
    "min_span_m": 30.0,
    "max_span_m": 150.0,
    "angle_pole_threshold_deg": 10.0
  },
  "scoring_weights": {
    "route_length_weight": 0.40,
    "electrical_loss_weight": 0.25,
    "cable_loading_weight": 0.20,
    "voltage_margin_weight": 0.15
  }
}
```

### Response Schema (`OptimisationResponse`)

```json
{
  "request_id": "req-8921-prod",
  "status": "success",
  "scenario": "Balanced",
  "schema_version": "2.0",
  "workflow_status": "SUCCESS",
  "feeder_routes_geojson": {
    "type": "FeatureCollection",
    "features": [
      {
        "type": "Feature",
        "geometry": {
          "type": "LineString",
          "coordinates": [[77.2090, 28.6139], [77.2302, 28.6301]]
        },
        "properties": {
          "feederName": "F1",
          "segmentId": "SEG-F1-001",
          "length_m": 2738.4,
          "traversal_cost": 2738.4,
          "active_loss_kw": 18.42,
          "pole_count": 28
        }
      }
    ]
  },
  "poles_geojson": {
    "type": "FeatureCollection",
    "features": [
      {
        "type": "Feature",
        "geometry": { "type": "Point", "coordinates": [77.2090, 28.6139] },
        "properties": {
          "pole_identifier": "P-F1-001",
          "feeder_name": "F1",
          "pole_role": "TERMINAL",
          "recommended_pole_type": "11m_steel_tubular_terminal"
        }
      }
    ]
  },
  "metrics": {
    "feeder_count": 1,
    "total_length_m": 2738.4,
    "estimated_cost": 142500.0,
    "message": "Optimization completed successfully. Projected into WGS 84 / UTM zone 43N."
  },
  "recommended_result": {
    "schema_version": "1.0.0",
    "project_id": "93b1d1e4-6b22-47ec-a4b5-128214227f42",
    "network_summary": {
      "wtg_count": 2,
      "feeder_count": 1,
      "segment_count": 1,
      "total_route_length_m": 2738.4
    },
    "pole_summary": {
      "total_poles": 28,
      "terminal_poles": 2,
      "angle_poles": 4,
      "intermediate_poles": 22,
      "junction_poles": 0
    },
    "spatial_constraint_summary": {
      "hard_exclusion_violation_count": 0,
      "soft_constraint_intersection_count": 1,
      "soft_constraint_overlap_length_m": 42.5,
      "road_crossing_count": 1,
      "affected_parcel_count": 3,
      "affected_parcel_overlap_length_m": 840.2
    },
    "electrical_summary": {
      "converged": true,
      "valid": true,
      "solver_algorithm": "nr",
      "total_active_loss_mw": 0.01842,
      "total_reactive_loss_mvar": 0.00912,
      "minimum_voltage_pu": 0.9842,
      "maximum_voltage_pu": 1.0000,
      "maximum_loading_percent": 34.2,
      "violation_count": 0
    },
    "feeders": [
      {
        "feeder_id": "F1",
        "wtg_ids": ["WTG-001", "WTG-002"],
        "segment_ids": ["SEG-F1-001"],
        "wtg_count": 2,
        "segment_count": 1,
        "route_length_m": 2738.4,
        "active_loss_mw": 0.01842,
        "reactive_loss_mvar": 0.00912,
        "minimum_voltage_pu": 0.9842,
        "maximum_voltage_pu": 1.0000,
        "maximum_loading_percent": 34.2,
        "valid": true,
        "violations": []
      }
    ],
    "violations": [],
    "source_crs": "EPSG:32643"
  }
}
```

---

## 3. Explicit Engineering Endpoint (`/api/v2/optimise`)

The explicit v2 API provides granular control over cable inventories, multi-candidate scoring weights, land cost policies, and lifecycle economics.

- **URL**: `/api/v2/optimise`
- **Method**: `POST`
- **Content-Type**: `application/json`

### Request Schema (`OptimiseProjectRequest`)

```json
{
  "request_id": "req-v2-1001",
  "project_id": "93b1d1e4-6b22-47ec-a4b5-128214227f42",
  "wtg_geojson": { "type": "FeatureCollection", "features": [] },
  "substation_geojson": { "type": "FeatureCollection", "features": [] },
  "avoidance_geojson": { "type": "FeatureCollection", "features": [] },
  "routing_config": {
    "resolution_m": 15.0,
    "padding_m": 500.0,
    "avoidance_buffer_m": 15.0,
    "avoidance_cost_weight": 25.0,
    "row_width_m": 18.0
  },
  "pole_config": {
    "target_span_m": 100.0,
    "min_span_m": 30.0,
    "max_span_m": 120.0,
    "angle_pole_threshold_deg": 10.0
  },
  "operating_point_config": {
    "operating_factor": 1.0,
    "power_factor": 0.95,
    "power_factor_mode": "lagging"
  },
  "cable_config": {
    "nominal_voltage_kv": 33.0,
    "slack_voltage_pu": 1.0,
    "min_voltage_pu": 0.95,
    "max_voltage_pu": 1.05,
    "system_base_mva": 100.0,
    "cable_types": [
      {
        "cable_type_id": "AL_300_XLPE",
        "resistance_ohm_per_km": 0.130,
        "reactance_ohm_per_km": 0.112,
        "capacitance_nf_per_km": 190.0,
        "max_current_a": 460.0,
        "parallel_count": 1,
        "derating_factor": 0.90
      }
    ],
    "default_cable_type_id": "AL_300_XLPE"
  },
  "scenario_config": {
    "candidate_count": 3
  },
  "engineering_scoring_weights": {
    "physical_weight": 0.30,
    "spatial_weight": 0.30,
    "infrastructure_weight": 0.15,
    "electrical_weight": 0.25,
    "spatial_subweights": {
      "traversal_cost": 0.40,
      "affected_parcels": 0.30,
      "road_crossings": 0.20,
      "soft_overlap_length": 0.10
    },
    "electrical_subweights": {
      "active_loss": 0.45,
      "cable_loading": 0.35,
      "voltage_margin": 0.20
    }
  },
  "costing_config": {
    "catalogue": {
      "catalogue_id": "IN-2026-Q3",
      "version": "1.2",
      "currency": "USD",
      "price_basis_date": "2026-08-01",
      "conductor_items": [
        {
          "cable_type_id": "AL_300_XLPE",
          "installed_cost_per_km_per_parallel_circuit": 28500.0
        }
      ],
      "pole_items": [
        { "pole_type": "terminal", "installed_cost_each": 3200.0 },
        { "pole_type": "angle", "installed_cost_each": 2400.0 },
        { "pole_type": "intermediate", "installed_cost_each": 1500.0 },
        { "pole_type": "junction", "installed_cost_each": 3800.0 }
      ],
      "land_policy": {
        "fixed_cost_per_affected_parcel": 500.0,
        "variable_basis": "ROW_INTERSECTION_AREA_M2",
        "variable_rate": 2.50
      }
    },
    "lifecycle": {
      "currency": "USD",
      "energy_price_basis_date": "2026-08-01",
      "analysis_period_years": 25,
      "discount_rate": 0.08,
      "annual_operating_hours": 8760,
      "loss_load_factor": 0.35,
      "energy_price_per_mwh": 48.50
    }
  },
  "cost_aware_config": {
    "engineering_weight": 0.70,
    "lifecycle_cost_weight": 0.30
  }
}
```

---

## Detailed Model Schemas

### `avoidance_geojson` Feature Contract
Avoidance layers represent spatial barriers rasterized into the A* cost surface:
- **`RESTRICTED_AREA`**: Hard exclusion zones. Rendered with infinite cost ($\infty$) and expanded by `buffer_m` (default: 10 m).
- **`ROAD` & `HT_LINE`**: Linear soft crossing constraints. Incur crossing cost penalties (`cost_weight`, default: 20.0).
- **`WATERCOURSE`**: Hydrographic features penalized heavily in environmental scenarios.
- **`PARCEL`**: Cadastral parcel polygons penalized heavily in minimum land impact scenarios.

### `SpatialConstraintSummary`
```typescript
interface SpatialConstraintSummary {
  hard_exclusion_violation_count: number;
  soft_constraint_intersection_count: number;
  soft_constraint_overlap_length_m: number;
  road_crossing_count: number;
  affected_parcel_count: number;
  affected_parcel_overlap_length_m: number;
}
```

### `ScoringWeightsRequest` Rules
- Weights (`route_length_weight`, `electrical_loss_weight`, `cable_loading_weight`, `voltage_margin_weight`) are strict floats between 0.0 and 1.0.
- **Invariant**: The four weights must sum to exactly `1.0` within numerical tolerance ($\epsilon = 10^{-9}$), otherwise Pydantic raises HTTP 422.

---

## Error Handling & HTTP Status Codes

| Status Code | Reason | Example Trigger |
| :--- | :--- | :--- |
| `200 OK` | Optimization solved successfully | Feasible candidate topologies generated and validated |
| `422 Unprocessable Entity` | Spatial infeasibility or invalid schema | WTGs placed inside hard restricted areas; disconnected graph; invalid weights sum ($\ne 1.0$) |
| `500 Internal Server Error` | Unhandled mathematical solver exception | Pandapower solver convergence anomaly |

---

## Related Notes

- [[Python Engine]] — Internal pipeline implementation, A* pathfinding, and Pandapower models.
- [[Backend]] — Spring Boot client calling this microservice.
- [[System Overview]] — End-to-end architecture.
