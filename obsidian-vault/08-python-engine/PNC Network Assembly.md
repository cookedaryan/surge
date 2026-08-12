# PNC Network Assembly

**Ticket:** SURGE-PY-014  
**Module:** `optimisation-python/app/pnc/`  
**Status:** Implemented

---

## Overview

The `pnc/` package provides the orchestration layer that converts the
individually generated feeder networks produced by the algorithm modules into
one complete **Project PNC Network**.

The caller provides:

```
WTG coordinates + Substation coordinates + feeder_capacity_mw + CostSurface
```

and receives back a fully assembled, validated `ProjectPNCNetwork` object.

---

## Package Structure

```
app/pnc/
├── __init__.py       # public surface
├── errors.py         # PNCAssemblyError + PNCAssemblyErrorCode
├── models.py         # PNCSegment, PNCFeeder, ProjectPNCNetwork
├── assembly.py       # build_pnc_network() + assemble_pnc_network()
└── geojson.py        # network_to_feature_collection() converter
```

---

## Entry Point

```python
from app.pnc import build_pnc_network

network = build_pnc_network(
    project_id="PROJECT-001",
    project=project_spatial_data,
    feeder_capacity_mw=50.0,
    cost_surface=cost_surface,
)
```

### Internal Pipeline

```
group_wtgs()                → FeederGroupingResult
build_project_graph()       → nx.Graph
build_feeder_mst()          → CollectorTopologyResult
route_collector_topology()  → PhysicalRoutingResult
refine_routing_result()     → RefinedRoutingResult
_build_pnc_network()        → ProjectPNCNetwork   ← validate + assemble
```

All algorithm calls delegate to existing modules. Zero algorithm logic is
duplicated in this package.

---

## Domain Models

### `PNCSegment`

| Field | Type | Description |
|---|---|---|
| `segment_id` | `str` | `SEG-FDR001-0001` (deterministic) |
| `feeder_id` | `str` | Parent feeder, e.g. `FDR-001` |
| `from_node_id` | `str` | Source node ID |
| `to_node_id` | `str` | Target node ID |
| `route_geometry` | `LineString` | Physical A* route (projected CRS) |
| `route_length_m` | `float` | Length of the physical route |
| `segment_type` | `Literal` | `substation_to_wtg` or `wtg_to_wtg` |

### `PNCFeeder`

| Field | Type | Description |
|---|---|---|
| `feeder_id` | `str` | `FDR-001` |
| `substation_id` | `str` | Node ID of the substation |
| `wtg_ids` | `tuple[str, ...]` | Sorted WTG node IDs |
| `ordered_node_ids` | `tuple[str, ...]` | BFS traversal from substation |
| `segments` | `tuple[PNCSegment, ...]` | All routed segments |
| `total_length_m` | `float` | Sum of segment lengths |
| `mst_graph` | `nx.Graph` | Authoritative MST topology graph |

### `ProjectPNCNetwork`

| Field | Type | Description |
|---|---|---|
| `project_id` | `str` | Caller-supplied |
| `substation_id` | `str` | Node ID |
| `substation_geometry` | `Point` | Projected CRS |
| `feeders` | `tuple[PNCFeeder, ...]` | All feeders, sorted |
| `wtg_coordinates` | `dict[str, Point]` | Node ID → projected Point |
| `total_route_length_m` | `float` | Sum across all feeders |
| `feeder_count` | `int` | |
| `wtg_count` | `int` | |
| `segment_count` | `int` | |
| `crs` | `pyproj.CRS` | Projected CRS |
| `route_length_by_feeder` | `dict[str, float]` | Per-feeder length |
| `wtg_count_by_feeder` | `dict[str, int]` | Per-feeder WTG count |

---

## GeoJSON Converter

```python
from app.pnc import network_to_feature_collection

fc = network_to_feature_collection(network)  # defaults to WGS-84 output
```

Returns a GeoJSON `FeatureCollection` with:

- `Point` for substation (`feature_type: "pnc_substation"`)
- `Point` per WTG (`feature_type: "pnc_wtg"`, includes `feeder_id`)
- `LineString` per segment (`feature_type: "pnc_segment"`, includes
  `segment_id`, `feeder_id`, `from_node`, `to_node`, `length_m`)

Pass `output_crs=None` to skip CRS conversion and keep projected coordinates.

---

## Failure Model

Assembly fails explicitly with `PNCAssemblyError` if:

| Code | Meaning |
|---|---|
| `FEEDER_WITHOUT_SUBSTATION_CONNECTION` | A feeder doesn't reach the substation |
| `UNROUTED_TOPOLOGY_EDGE` | A topology edge has no physical route |
| `ORPHAN_WTG` | A project WTG is absent from all feeders |
| `DUPLICATE_WTG_ASSIGNMENT` | A WTG appears in two feeders |
| `UNKNOWN_FEEDER_SEGMENT` | A segment's feeder_id doesn't match its parent feeder |
| `INVALID_NETWORK_CONNECTIVITY` | General structural integrity failure |
| `DUPLICATE_SEGMENT_ID` | Same segment ID appears more than once |

A partially assembled network **never** looks like a valid `ProjectPNCNetwork`.

---

## Stable ID Scheme

| Object | Pattern | Example |
|---|---|---|
| Feeder | `FDR-{N:03d}` | `FDR-001` |
| Segment | `SEG-{feeder_suffix}-{N:04d}` | `SEG-FDR001-0001` |

Identical inputs always produce identical IDs.

---

## Topology Authority

The `mst_graph` field on every `PNCFeeder` is the MST produced by
`build_feeder_mst()` and is **never reconstructed from geometry**. All topology
queries should use this graph directly.

`ordered_node_ids` is a deterministic BFS traversal convenience — the
underlying graph remains authoritative.

---

## Out of Scope

- Pandapower / AC load-flow
- Voltage-drop simulation
- Cable sizing
- Frontend map implementation
- Database persistence
- Manual feeder editing UI
