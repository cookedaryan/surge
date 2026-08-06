# System Architecture Overview

SURGE uses a microservices architecture separating system orchestration and API management (Java Spring Boot) from computational optimization and spatial math (Python FastAPI Engine).

```text
                       WEB GIS CLIENT
          Map, WTG input, layers, scenarios, comparison
                               │
                          REST / GeoJSON
                               │
                     JAVA SPRING BOOT API
      Authentication, projects, jobs, persistence, reports
                               │
            ┌──────────────────┴─────────────────┐
            │                                    │
        PostGIS                           Python FastAPI
   Spatial/project data              Optimisation service
                                              │
                               ┌──────────────┼──────────────┐
                               │              │              │
                            GIS engine   Routing engine   Electrical engine
                            GeoPandas    A* / MST         pandapower
```

---

## Service Responsibilities

- **Java Spring Boot API**: Manages authentication, project workspace lifecycle, job queues, PDF report generation, and PostGIS data persistence.
- **Python FastAPI Engine**: Executes WTG clustering, multi-objective spatial pathfinding (A*/MST), pole placement algorithms, and pandapower load flow analysis.
- **PostGIS Database**: Relational and geospatial database serving spatial layers, raster DEMs, and optimization job results.
- **Web GIS Client**: Interactive frontend for uploading GIS files, visualizing routes, configuring weights, and comparing scenarios side-by-side.

---

## Related Notes
- [[Backend]]
- [[Python Engine]]
- [[Frontend]]
- [[Database]]
- [[Deployment]]
