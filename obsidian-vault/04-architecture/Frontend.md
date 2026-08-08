# Frontend Architecture (Web GIS Dashboard)

Source Code:
`web-map/`

## Tech Stack
- **Framework & Tooling**: Vite, HTML5, Vanilla JavaScript (ES modules)
- **Mapping Engine**: Leaflet 1.9.4 with OpenStreetMap vector tiles & custom GeoJSON layers
- **Styling**: Vanilla CSS Design System with dark glassmorphism palette, responsive layout, micro-animations, and Google Inter font

## Implemented Capabilities (2026-08-08)
- **Interactive Web GIS Canvas**: Visualizes Wind Turbines (WTGs), Substations, Feeder Line Paths (LineString), Cadastral Parcels (Polygons), and Restricted Avoidance Areas.
- **Drag-and-Drop Ingestion**: Instant drag-and-drop parser for RFC 7946 GeoJSON files with auto-zoom bounds fitting.
- **Optimization Control Panel**: Slider controls for Feeder Capacity (MVA), Max Span (m), System Voltage (kV), and objective weightings (Cost vs Loss vs Land).
- **Backend API Integration**: Connects dynamically to Java Spring Boot REST endpoints (`/api/v1/projects`, `/assets`, `/jobs`, `/routes`, `/reports`).
- **Live Summary & BOM Card**: Dynamic metrics displaying Total Route Length (km), Capex Cost ($), Electrical Power Losses (kW), Land ROW Cost ($), and Pole Count.
- **CSV Export**: Direct one-click download for engineering Bill of Materials CSV reports.

---

## Next Frontend Tasks

1. **Multi-Scenario Comparison Matrix**: Side-by-side card & map overlay comparing candidate route scenarios.
2. **Interactive Vertex Tweaking**: Allow users to drag feeder route vertices on the map and calculate modified cost/loss in real-time.
3. **Elevation Profile Viewer**: Charts showing route elevation profiles derived from Python DEM rasters.
4. **WebSocket Progress Notifications**: Real-time progress bar for active optimization jobs.

---

## Related Notes
- [[System Overview]]
- [[Backend]]
