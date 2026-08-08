# ADR-006: Spatial Models and Unified UTM Projection

## Status
**Accepted**

## Context
The SURGE Python optimisation service requires high-precision metric calculations (distances, areas, slopes, buffers) to properly generate NetworkX graphs, route paths via $A^*$, and place individual electrical poles. 
Input from the Java API is provided strictly in standard WGS84 GeoJSON (`EPSG:4326`) because this is the global standard format for exchanging web-map data.

Working directly on WGS84 decimal degrees for algorithm calculations would result in wildly inaccurate electrical cable measurements.

## Decision
1. **Early Domain Translation**: The Python service will immediately parse incoming API GeoJSON requests and translate them into deeply validated Python frozen `dataclasses` (e.g., `WindTurbine`, `Substation`, `ProjectSpatialData`). Graph routing algorithms will operate purely on these strong types, completely decoupled from GeoJSON dictionary manipulation.
2. **One-Project-One-UTM**: Rather than independently projecting each WTG into a UTM zone (which could cause coordinates to split across zone boundaries, breaking math consistency), the system will calculate the geographic centroid of all project inputs. It will then select a *single, unified dynamic UTM projection* (e.g., `EPSG:32644`) for the entire project site and project all inputs into this shared coordinate space.

## Consequences
**Pros:**
* All internal algorithms (graph distances, raster overlays, buffering) can rely on perfectly consistent Pythagorean math (`a^2 + b^2 = c^2`) because coordinates are stored uniformly in meters.
* The algorithm core is protected from dirty incoming JSON.

**Cons:**
* Requires a strict translation boundary before algorithms can start, and a strict translation back to WGS84 before API output.
* If a project geographically spans hundreds of miles (crossing multiple UTM zones), edge-case distortions may occur on the outer boundaries. (Acceptable for typical wind/solar farm footprints).
