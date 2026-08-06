# Functional Requirements

## 1. GIS & Spatial Ingestion
- **FR-01**: System shall import GeoJSON/Shapefile data for WTG locations, substations, terrain DEM, roads, forests, and cadastral parcels.
- **FR-02**: System shall automatically calculate slope cost factors from elevation rasters.

## 2. Network Routing & Optimization
- **FR-03**: System shall group WTGs into feeders based on electrical load limits and geographical proximity.
- **FR-04**: System shall generate optimal feeder routes avoiding restricted forest polygons and minimizing slope.
- **FR-05**: System shall calculate ROW corridor area and compensation cost per parcel.

## 3. Electrical Simulation & Verification
- **FR-06**: System shall run pandapower load flow analysis on generated feeder paths.
- **FR-07**: System shall flag any voltage drop exceeding 5% or conductor thermal overload.

## 4. Pole Placement & Selection
- **FR-08**: System shall place poles dynamically based on span limits, terrain profile, and angle changes.
- **FR-09**: System shall select pole structural types (Suspension, Tension, Terminal).

---

## Related Notes
- [[Non Functional Requirements]]
- [[User Stories]]
- [[Constraints]]
