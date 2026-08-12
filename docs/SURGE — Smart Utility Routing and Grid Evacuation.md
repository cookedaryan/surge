# SURGE — Smart Utility Routing and Grid Evacuation

## Product Vision

SURGE is intended to help engineers design renewable-energy collector and evacuation networks. The target product combines GIS, electrical analysis, mathematical optimization, and explainable decision support. It aims to compare complete engineering alternatives rather than merely draw the shortest line between turbines and a substation.

The target lifecycle includes WTG grouping, radial feeder topology, geographic routing, pole placement, variable spans, electrical constraints, land and Right-of-Way (ROW) impact, lifecycle cost, and scenario comparison.

## Current Repository Baseline

The long-term capabilities above are not all implemented. As of 2026-08-12:

- The Vite/vanilla-JavaScript/Leaflet client can manage projects, upload and display GeoJSON, submit jobs, and display report data. Several API failures use demo fallbacks.
- The Java 21/Spring Boot backend persists projects and spatial assets in PostGIS, synchronously calls Python, stores jobs/routes, and aggregates BOM/CSV data.
- The Python/FastAPI service validates WTG and substation Points, projects them into one UTM CRS, creates a complete candidate graph, and groups WTGs with K-Means-assisted MILP.
- Python currently returns cost-surface-aware routed LineStrings over a uniform base surface. Standalone PNC assembly, pandapower AC load-flow validation, map-ready result packaging, and deterministic candidate PNC generation are implemented. Raw terrain/restriction rasterization, lifecycle scoring, ML ranking, and API integration of the richer result remain planned.
- Authentication, asynchronous processing, CI/CD, Kubernetes, and production deployment controls remain planned.

## How the Components Work Together

1. The browser exchanges REST and WGS84 GeoJSON with Spring Boot.
2. Spring Boot validates workflows and persists spatial/application state in PostGIS.
3. A job request causes Spring Boot to serialize stored WTGs and substations and call Python.
4. Python converts geographic coordinates to a metric UTM space before graph and grouping calculations.
5. Java stores returned metrics and any route features, then the browser refreshes map and report views.

This split keeps authentication, transactions, and project ownership in Java while keeping scientific types and solvers in Python.

## Core Concepts

- **Collector network**: the electrical network carrying generation from WTGs toward a substation.
- **Feeder**: a branch of that network with an electrical capacity limit.
- **Topology**: which assets connect, independent of the physical corridor.
- **Route**: the geographic LineString used to realize a topology connection.
- **ROW corridor**: the land strip required around a route for construction, operation, and clearance.
- **Multi-objective optimization**: comparing alternatives across competing metrics such as cost, land, environment, and electrical performance.
- **Explainability**: preserving inputs, constraints, raw metrics, weights, algorithms, and rejection reasons so a result can be audited.

## Documentation Model

The Obsidian vault is the detailed architecture and decision record. Notes explicitly label behavior as Implemented, Partial, or Planned. This document provides the stable product overview; implementation-level contracts belong in the vault and service source documentation.
