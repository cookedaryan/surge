# PNC Network Assembly

**Ticket:** SURGE-PY-014  
**Module:** `optimisation-python/app/pnc/`

---

## What is it?

The `pnc/` package is the orchestration layer that converts the output of
individual feeder-network algorithms into a single, complete **Project PNC
Network**.

For the full pipeline, the caller provides projected spatial data, feeder
capacity, and a prepared cost surface:

```python
from app.pnc import build_pnc_network

network = build_pnc_network(
    project_id="PROJECT-001",
    project=project_spatial_data,
    feeder_capacity_mw=50.0,
    cost_surface=cost_surface,
)
```

The result is a validated `ProjectPNCNetwork` containing all feeders, all
routed segments with their physical `LineString` geometries, WTG coordinates,
and project-wide metrics — ready for GeoJSON export or API delivery.

---

## Package

```
optimisation-python/app/pnc/
├── __init__.py       # public surface
├── errors.py         # PNCAssemblyError, PNCAssemblyErrorCode
├── models.py         # PNCSegment, PNCFeeder, ProjectPNCNetwork
├── assembly.py       # build_pnc_network() + assemble_pnc_network()
└── geojson.py        # network_to_feature_collection()
```

## Tests

```
optimisation-python/tests/test_pnc_assembly.py
```

33 tests covering:
- One feeder (linear chain)
- Multiple feeders
- Branched feeder topology
- Missing physical route → must fail
- Orphan WTG → must fail
- Duplicate WTG assignment → must fail
- GeoJSON output structure
- Determinism (same input → same IDs + ordering)

---

## GeoJSON Output

```python
from app.pnc import network_to_feature_collection

fc = network_to_feature_collection(network)  # WGS-84 by default
```

Produces a `FeatureCollection` with:

- `pnc_substation` — Point
- `pnc_wtg` — Point per turbine, includes `feeder_id`
- `pnc_segment` — LineString per cable segment, includes `segment_id`,
  `feeder_id`, `from_node`, `to_node`, `length_m`

---

## ID Scheme

| Object | Format | Example |
|---|---|---|
| Feeder | `FDR-{N:03d}` | `FDR-001` |
| Segment | `SEG-{feeder_suffix}-{N:04d}` | `SEG-FDR001-0001` |

Deterministic: identical inputs always produce identical IDs.

---

## Failure Model

`PNCAssemblyError` is raised (never silently dropped) for:

- `FEEDER_WITHOUT_SUBSTATION_CONNECTION`
- `UNROUTED_TOPOLOGY_EDGE`
- `ORPHAN_WTG`
- `DUPLICATE_WTG_ASSIGNMENT`
- `UNKNOWN_FEEDER_SEGMENT`
- `INVALID_NETWORK_CONNECTIVITY`
- `DUPLICATE_SEGMENT_ID`

A partial network is never returned as a successfully assembled network.

---

## Architecture Notes

- The `mst_graph` on every `PNCFeeder` is the authoritative topology.
  Topology is **never reconstructed from geometry**.
- `ordered_node_ids` is a deterministic BFS convenience; it does not replace
  the graph.
- Zero algorithm logic is duplicated — the orchestrator calls `group_wtgs`,
  `build_feeder_mst`, `route_collector_topology`, and `refine_routing_result`
  from their existing modules.
