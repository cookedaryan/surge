# ADR-001: Use FastAPI for the Optimization Service

- **Status**: Accepted and implemented
- **Date**: 2026-08-04

## Context

The optimization service needs Python libraries for geometry, projections, graphs, numerical optimization, raster processing, electrical analysis, and later machine learning. The Java backend needs a stable, language-neutral way to invoke those calculations.

## Decision

Implement the computation boundary as a Python FastAPI service with versioned JSON/GeoJSON endpoints. Keep public project workflows and persistence in Spring Boot.

## Why FastAPI

- Native integration with Pydantic request and response models
- Automatic OpenAPI generation during development
- Straightforward synchronous endpoints for the current pipeline
- Low ceremony around ordinary Python scientific code

FastAPI was not selected to make CPU-bound solvers automatically fast or asynchronous. Heavy future optimization will require an explicit worker and resource-management design.

## Consequences

- **Positive**: Python scientific types remain behind a typed HTTP boundary.
- **Positive**: Java and Python can be tested and deployed independently.
- **Negative**: Both services must maintain compatible field names, scenarios, validation, and error behavior.
- **Negative**: Network failures and timeouts become part of the application workflow.

## Implementation

`app/main.py` builds the application, `app/api/v1/router.py` registers health and optimize routes, and Pydantic models define the contract. Swagger/ReDoc are disabled in production mode.
