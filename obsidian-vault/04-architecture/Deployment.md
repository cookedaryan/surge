# Deployment Architecture

## Current Status

The repository provides a local Docker Compose stack for PostGIS, the Java backend, and the Python optimizer. It does not currently provide a frontend container, reverse proxy, Kubernetes manifests, CI/CD workflow, cloud infrastructure, or production secret management.

## Docker Compose Services

| Service | Container role | Port | Dependencies |
| --- | --- | --- | --- |
| `db` | PostgreSQL 16 with PostGIS 3.4 | `5432` | Persistent named volume |
| `backend` | Java 21 Spring Boot API | `8080` | Waits for the database health check |
| `optimizer` | Python FastAPI service | `8000` | No Compose dependency declaration |

The backend receives `PYTHON_ENGINE_URL=http://optimizer:8000`. The Python container runs with `ENVIRONMENT=production`, which disables its Swagger and ReDoc pages. Database credentials have development defaults and must be overridden outside local development.

The web client is started separately with `npm run dev`. Because its API URL is currently hard-coded to localhost, a hosted deployment will require configurable frontend environment handling or a same-origin reverse proxy.

## Local Request Path

```text
Browser/Vite -> localhost:8080 backend -> db:5432
                                   \-> optimizer:8000
```

## Production Concerns Not Yet Implemented

- TLS termination and a public routing layer
- Secret storage and credential rotation
- Service-to-service authentication or network policies
- Database backups, recovery testing, and migration rollout strategy
- Worker/queue architecture for long-running jobs
- Resource limits for CPU- and memory-intensive optimization
- Structured logs, metrics, tracing, and alerting
- CI checks and reproducible image publication
- Horizontal scaling and Kubernetes manifests

## Related Notes

- [[System Overview]]
- [[Backend]]
- [[Python Engine]]
