# ADR-005: Layer the Python Service and Use Pydantic 2 Contracts

- **Status**: Accepted and implemented
- **Date**: 2026-08-06
- **Deciders**: SURGE Engineering Team

## Context

Putting parsing, validation, geometry work, and algorithms directly inside a FastAPI endpoint would couple solver code to HTTP dictionaries and make it difficult to test independently. Mutable defaults and weakly typed response maps would also make the contract fragile.

## Decision

Separate the Python service into API, schema, service, GIS, domain-model, algorithm, configuration, and utility layers.

- Pydantic 2 models define external JSON contracts and numeric constraints.
- Frozen dataclasses hold internal projected spatial state.
- Endpoints delegate orchestration to `OptimisationService`.
- Algorithm modules accept domain objects rather than GeoJSON dictionaries.
- `request_id` correlates a Java job call with its Python response.
- Dependencies are pinned for repeatable local/container environments.

## Why Two Model Families?

Pydantic is suited to untrusted external data and JSON serialization. Frozen dataclasses are small, explicit internal values that can carry Shapely and pyproj objects without implying they are API schemas. The translation boundary makes units and validation visible before algorithms run.

## Consequences

- **Positive**: Each layer has focused tests and limited reasons to change.
- **Positive**: Algorithms are independent of FastAPI and transport naming.
- **Positive**: External validation errors are consistent HTTP 422 responses.
- **Negative**: Field additions may require coordinated Pydantic, Java DTO, service, and documentation changes.
- **Negative**: Some validation currently occurs after Pydantic, so error formats differ between schema and domain failures.

## Implementation Notes

The current algorithm package also contains `wtg_grouping.py`; GIS code lives under `app/gis`, and internal spatial dataclasses live under `app/models`. The response exposes feeder count but not the full internal group assignments.
