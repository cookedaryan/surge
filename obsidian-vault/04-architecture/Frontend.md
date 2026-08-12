# Frontend Architecture (Web GIS Dashboard)

## Role

`web-map` is a browser client for project selection, GeoJSON upload, optimization controls, map visualization, and report download. It is implemented with Vite, vanilla JavaScript modules, CSS, and Leaflet 1.9.4; it is not a React application.

## Modules

- `src/api.js`: wraps Java backend HTTP calls and supplies demonstration fallbacks for several failed reads.
- `src/app.js`: coordinates DOM events, project selection, uploads, job submission, map refreshes, and BOM cards.
- `src/map.js`: owns the Leaflet map, basemaps, layer groups, styling, popups, visibility, and fit-to-bounds behavior.
- `src/index.css`: responsive visual design and component styling.

## Map Concepts

**GeoJSON** is the interchange format used for points, lines, and polygons. GeoJSON coordinates are ordered longitude then latitude, while Leaflet callbacks expose latitude then longitude.

**Layer groups** keep WTGs, substations, routes, parcels, and restricted areas independent. A checkbox can add or remove one group without rebuilding the other layers.

**Basemaps** provide geographic context underneath project data. The current Carto and Esri tile layers require external network access and carry their own attribution requirements.

## User Flow

1. Load projects from the Java API and select the first result.
2. Fetch stored assets, parcels, restricted areas, routes, and a BOM summary.
3. Render each GeoJSON collection into its corresponding Leaflet layer.
4. Upload an asset, parcel, or restricted-area file through the selected import endpoint.
5. Submit scenario and electrical parameters to create an optimization job.
6. Refresh map and report data after the client-side progress sequence completes.

## Demo Fallbacks

`api.js` catches failures for projects, spatial reads, job submission, routes, and reports and substitutes Gujarat demonstration data. This keeps the interface visually usable while services are unavailable, but it can make an outage look like a successful calculation. Production behavior should display explicit loading and error states and reserve demo data for an intentional demo mode.

## Progress Behavior

The displayed optimization progress is simulated with fixed percentages and `setTimeout`; it does not poll job status or receive server events. The message mentioning A* is aspirational because the current Python pipeline does not implement A*.

## Configuration and Security Limitations

- API base URL is hard-coded to `http://localhost:8080/api/v1`.
- No authentication token is sent.
- Error handling uses browser alerts and console messages.
- Popup HTML interpolates feature properties directly; untrusted uploaded values should be escaped before production use.
- The frontend has no test suite in the current repository.

## Planned Improvements & Web Map UI Task Backlog

- **SURGE-FE-001: Interactive Multi-Layer Web GIS Map**
  - Add layer control toggles: Feeder routes (color-coded by feeder ID), Pole locations with distinct SVG icons (Terminal, Angle, Intermediate), Cadastral parcel boundary overlays with parcel ID tooltips, Restricted area polygons, DEM slope surface heatmap toggle.
- **SURGE-FE-002: Route Scenario Comparison Dashboard**
  - Implement side-by-side comparison modal/view comparing candidate routes across Capex, ROW compensation, Power losses, line length, and pole count.
  - Interactive scenario selector switching active map routes cleanly.
- **SURGE-FE-003: Real-Time Optimization Status & Progress UI**
  - Add an interactive progress overlay displaying step-by-step optimization status (e.g. *Preprocessing GIS data -> Clustering WTGs -> Computing A* Cost Surface -> Placing Poles -> Running pandapower Load Flow*).
- **SURGE-FE-004: Interactive Pole/Route Nudging & Re-validation**
  - Enable dragging pole markers on the map to manually adjust route points and trigger incremental re-validation requests.
- **SURGE-FE-005: Visual Excellence & Micro-Animations**
  - Refine glassmorphism aesthetic, sleek dark mode color palettes, custom Leaflet SVG markers, active state animations, dynamic stats widgets, and responsive layout scaling.
- **SURGE-QA-003: Automated Web Map Testing & Verification**
  - Component & UI behavior testing with `Vitest` / `Playwright`.
  - End-to-end user workflow testing (GeoJSON upload -> scenario execution -> map render -> BOM download).

## Related Notes

- [[System Overview]]
- [[Backend]]
- [[FastAPI Endpoints|FastAPI Microservice Specification]]

