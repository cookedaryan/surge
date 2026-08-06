# ADR-001: Use FastAPI for Optimization Engine

* Status: **Accepted**
* Date: 2026-08-04

## Context
The optimization core requires heavy geospatial computation (GeoPandas, Shapely, Rasterio) and electrical power network modeling (pandapower). The Python scientific ecosystem provides mature libraries for these tasks.

## Decision
Implement the optimization and routing microservice in **Python using FastAPI**, exposing REST endpoints for the Java Spring Boot orchestrator.

## Consequences
- **Positive**: Direct access to PyData/GIS/Pandapower ecosystem. Fast asynchronous execution via FastAPI.
- **Negative**: Requires IPC / REST contract maintenance between Java API and Python service.
