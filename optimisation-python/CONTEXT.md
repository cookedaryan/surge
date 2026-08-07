# Surge Optimisation Python — Project Context

> **Purpose:** This file contains the latest technical context of the project for Gemini Notebook, NotebookLM, Obsidian, developers, and future AI-assisted development.

---

## 1. Project Overview

### Project Name

Surge Optimisation Python

### Main Objective

The Python service is responsible for machine-learning, GIS processing, and
route-optimisation components of the Surge 33 kV electrical route-planning
system. It will expose these capabilities through FastAPI endpoints for
integration with the Java backend.

### Current Development Stage

* [ ] Initial setup
* [ ] MVP development
* [ ] Integration
* [ ] Testing
* [ ] Deployment
* [ ] Production

Current stage:

`MVP development`

### Last Major Update

**Date:** 2026-08-07

**Summary:**

Implemented the core GIS preprocessing pipeline, including dynamic one-project-one-UTM projection, geometry validation, GeoJSON parsing, and conversion of WTG/Substation data into strictly-typed spatial dataclasses (`app/models/spatial.py`).

---

## 2. Technology Stack

### Programming Language

* Python 3.11.9

### Backend Framework

* FastAPI
* Uvicorn

### Data Validation and Configuration

* Pydantic
* pydantic-settings

### Machine Learning and Optimisation

Status: Planned — not implemented

### Database

Status: Planned — not implemented

### External Integration

Status: Planned — not implemented

---

## 3. Current Directory Structure

Update this section whenever files or folders are added, moved, renamed, or deleted.

```text
optimisation-python/
+--- .dockerignore
+--- .env.example
+--- .gitignore
+--- AGENTS.md
+--- CONTEXT.md
+--- Dockerfile
+--- README.md
+--- app
|    +--- __init__.py
|    +--- algorithms
|    |    +--- __init__.py
|    |    +--- cost_function.py
|    |    +--- electrical_analysis.py
|    |    \--- route_graph.py
|    +--- gis
|    |    +--- __init__.py
|    |    +--- crs.py
|    |    +--- geojson.py
|    |    +--- geometry.py
|    |    \--- preprocessing.py
|    +--- models
|    |    +--- __init__.py
|    |    \--- spatial.py
|    +--- api
|    |         +--- __init__.py
|    |         +--- endpoints
|    |         |    +--- __init__.py
|    |         |    +--- health.py
|    |         |    \--- optimise.py
|    |         \--- router.py
|    +--- core
|    |    +--- __init__.py
|    |    \--- config.py
|    +--- main.py
|    +--- schemas
|    |    +--- __init__.py
|    |    \--- optimise.py
|    +--- services
|    |    +--- __init__.py
|    |    \--- optimisation_service.py
|    \--- utils
|         +--- __init__.py
|         \--- coordinate_transform.py
+--- notebooks
|    \--- .gitkeep
+--- pyproject.toml
+--- requirements.lock.txt
+--- requirements.txt
\--- tests
     +--- .gitkeep
     +--- __init__.py
     +--- test_health.py
     \--- test_optimise.py
```

### Important Directory Responsibilities

| Directory         | Responsibility                                          |
| ----------------- | ------------------------------------------------------- |
| `app/api/`        | FastAPI routes and request handling                     |
| `app/core/`       | Configuration, logging, and shared application settings |
| `app/models/`     | Internal models or database models                      |
| `app/schemas/`    | Pydantic request and response schemas                   |
| `app/services/`   | Business logic and external service integration         |
| `app/gis/`        | Geospatial data processing, validation, and CRS management|
| `app/algorithms/` | Route optimisation and graph algorithms                 |
| `app/ml/`         | Machine-learning models, training, and inference        |
| `app/utils/`      | Reusable helper functions                               |
| `tests/`          | Unit and integration tests                              |
| `data/`           | Local development datasets                              |
| `notebooks/`      | Experimental Jupyter notebooks                          |
| `scripts/`        | Setup, training, conversion, and maintenance scripts    |
| `docs/`           | Detailed technical documentation                        |

---

## 4. Application Entry Point

### Main File

```text
app/main.py
```

### Current Application Startup

```bash
uvicorn app.main:app --reload
```

### Main Application Responsibilities

* Create the FastAPI application.
* Register API routers.
* Configure middleware.
* Configure exception handlers.
* Run startup and shutdown logic.
* Provide health-check endpoints.

### Current Main Application Code Flow

```text
Application starts
        ↓
Environment configuration loads
        ↓
FastAPI application is created
        ↓
Middleware is registered
        ↓
API routers are registered
        ↓
Required models or services are initialised
        ↓
Application starts accepting requests
```

---

## 5. Environment Setup

### Required Python Version

```text
Python 3.11.9
```

### Virtual Environment Location

```text
optimisation-python/.venv
```

### Create the Environment

#### Windows CMD

```bat
py -3.11 -m venv .venv
.venv\Scripts\activate
python -m pip install --upgrade pip
pip install -r requirements.txt
```

### Run the Application

```bat
.venv\Scripts\activate
uvicorn app.main:app --reload
```

### Current Environment Variables

Never place real passwords, API keys, tokens, or secrets in this file.

```env
APP_NAME=Surge Optimisation Service
APP_ENV=development
DEBUG=true
HOST=127.0.0.1
PORT=8000
```

Add only variable names and safe example values.

---

## 6. Configuration Management

### Configuration File

```text
app/core/config.py
```

### Configuration Library

```text
pydantic-settings
```

### Configuration Responsibilities

* Load values from the `.env` file.
* Validate application settings.
* Provide typed settings throughout the application.
* Maintain separate development and production configuration.
* Prevent secrets from being hardcoded.

### Configuration Usage

```python
from app.core.config import settings
```

Describe any major changes to the configuration system here.

---

## 7. API Endpoints

Update this table whenever an endpoint is added, removed, renamed, or changed.

| Method | Endpoint                 | Purpose                     | Status  |
| ------ | ------------------------ | --------------------------- | ------- |
| GET    | `/`                      | Basic application response  | Active  |
| GET    | `/health`                | Service health check        | Implemented |
| POST   | `/api/v1/optimise`       | Generate an optimised route | Partial |
| POST   | `/api/v1/predict`        | Run an ML prediction        | Planned |

### Endpoint Details

#### `GET /`

**Purpose:**
Verify that the API is running.

**Example response:**

```json
{
  "message": "Surge Optimisation API is running"
}
```

#### `POST /api/v1/optimise-route`

**Purpose:**
Accept route, GIS, terrain, cost, and constraint data and return an optimised route.

**Expected input:**

```json
{
  "start": {
    "latitude": 0.0,
    "longitude": 0.0
  },
  "end": {
    "latitude": 0.0,
    "longitude": 0.0
  },
  "constraints": {}
}
```

**Expected output:**

```json
{
  "route": [],
  "distance": 0.0,
  "estimated_cost": 0.0,
  "warnings": []
}
```

Replace planned structures with the actual implementation when available.

---

## 8. Data Models and Schemas

List only important models and schemas.

### Example Schemas

| Schema           | File                    | Purpose                       |
| ---------------- | ----------------------- | ----------------------------- |
| `Coordinate`     | `app/schemas/route.py`  | Stores latitude and longitude |
| `RouteRequest`   | `app/schemas/route.py`  | Validates optimisation input  |
| `RouteResponse`  | `app/schemas/route.py`  | Defines optimisation output   |
| `HealthResponse` | `app/schemas/health.py` | Defines health-check output   |

### Validation Rules

Document important rules such as:

* Latitude must be between `-90` and `90`.
* Longitude must be between `-180` and `180`.
* Start and destination cannot be identical.
* Required GIS layers must be present.
* Invalid or empty route data must return a clear error.
* Optimisation constraints must remain inside configured limits.

---

## 9. Optimisation Pipeline

Update this section as the algorithm develops.

```text
Receive route request
        ↓
Validate coordinates and constraints
        ↓
Load GIS, road, terrain, and obstacle data
        ↓
Preprocess and normalise input data
        ↓
Build graph or search space
        ↓
Calculate edge costs
        ↓
Apply route optimisation algorithm
        ↓
Validate the generated path
        ↓
Calculate route metrics
        ↓
Return the final route
```

### Current Algorithms

Mark their current status.

| Algorithm         | Purpose                            | Status                    |
| ----------------- | ---------------------------------- | ------------------------- |
| Dijkstra          | Minimum-cost path                  | Planned — not implemented |
| A*                | Heuristic route search             | Planned — not implemented |
| Genetic Algorithm | Multi-objective route optimisation | Planned — not implemented |
| Machine Learning  | Cost or feasibility prediction     | Planned — not implemented |

### Route Cost Factors

The route cost may consider:

* Route length
* Terrain slope
* Elevation
* Land use
* Road crossings
* Rivers and water bodies
* Forest areas
* Buildings
* Protected areas
* Construction cost
* Maintenance cost
* Safety risk
* Accessibility
* Existing infrastructure
* Environmental impact

### Generic Cost Function

```text
Total Cost =
    w₁ × Distance Cost
  + w₂ × Terrain Cost
  + w₃ × Construction Cost
  + w₄ × Environmental Cost
  + w₅ × Safety Risk
  + w₆ × Constraint Penalty
```

Document the actual weights and equations when finalised.

---

## 10. Machine-Learning Pipeline

Status: Planned — not implemented

---

## 11. Java–Python Integration

Status: Planned — not implemented

---

## 12. Database and Storage

Status: Planned — not implemented

---

## 13. Important Files

Update this table after major structural changes.

| File                 | Purpose                                   |
| -------------------- | ----------------------------------------- |
| `app/main.py`        | FastAPI application entry point           |
| `app/core/config.py` | Application configuration                 |
| `requirements.txt`   | Python dependencies                       |
| `.env.example`       | Safe environment variable template        |
| `.gitignore`         | Files excluded from Git                   |
| `README.md`          | Installation and usage guide              |
| `PROJECT_CONTEXT.md` | Complete current AI and developer context |

Add important algorithm, ML, API, or service files as they are created.

---

## 14. Dependencies

### Current Dependencies

```text
fastapi
uvicorn
pydantic
pydantic-settings
```

Add dependencies only after they are installed and used.

### Install Dependencies

```bash
pip install -r requirements.txt
```

### Save Dependencies

```bash
pip freeze > requirements.txt
```

For a clean production project, manually review `requirements.txt` instead of keeping unnecessary packages.

---

## 15. Testing

### Current Test Status

* [ ] Unit tests created
* [ ] API tests created
* [ ] Integration tests created
* [ ] Optimisation tests created
* [ ] ML tests created

### Planned Test Structure

```text
tests/
├── test_main.py
├── test_config.py
├── test_routes.py
├── test_optimisation.py
└── test_ml.py
```

### Run Tests

```bash
pytest
```

### Important Test Cases

* API starts successfully.
* Health endpoint responds correctly.
* Invalid coordinates are rejected.
* Missing fields produce validation errors.
* Route generation returns a valid path.
* The optimiser handles cases where no route exists.
* ML model input has the correct shape.
* External service failures are handled safely.
* Java–Python request and response formats match.

---

## 16. Error Handling

Document important errors and their solutions.

### Error Record

#### Error

```text
Cannot run program ".venv\Scripts\python.exe":
The system cannot find the file specified.
```

#### Cause

PyCharm was configured to use a virtual-environment interpreter that no longer existed or had been moved.

#### Solution

* Remove the invalid interpreter from PyCharm.
* Create a new `.venv` using Python 3.11.
* Select `.venv\Scripts\python.exe` as the project interpreter.
* Reinstall dependencies.

### Current Known Errors

| Error             | Cause          | Status           |
| ----------------- | -------------- | ---------------- |
| Add an error here | Add the reason | Open or resolved |

Remove old errors when they are no longer useful, or move them to the change history.

---

## 17. PyCharm Configuration

### Current Interpreter

```text
optimisation-python\.venv\Scripts\python.exe
```

### Required Configuration

1. Open **File → Settings**.
2. Open **Project → Python Interpreter**.
3. Select **Add Interpreter**.
4. Choose **Existing Environment**.
5. Select:

```text
C:\Users\ARK\Documents\helloworld\surge\optimisation-python\.venv\Scripts\python.exe
```

### Working Directory

```text
C:\Users\ARK\Documents\helloworld\surge\optimisation-python
```

Update this section if the project directory changes again.

---

## 18. Git Tracking

### Repository Root

```text
C:\Users\ARK\Documents\helloworld\surge\optimisation-python
```

### Check Changes

```bash
git status
git diff
```

### Save Changes

```bash
git add -A
git commit -m "Describe the change"
```

### Files That Must Not Be Committed

```gitignore
.venv/
.env
__pycache__/
*.pyc
.idea/
.ipynb_checkpoints/
```

### Current Branch

```text
main
```

Change this when working on another branch.

---

## 19. Recent Major Changes

Keep approximately the latest 10–15 meaningful changes.

### 2026-08-06 — Python Environment Reconfigured

**Changed:**
- Removed the reference to the missing virtual environment.
- Created the virtual environment inside `optimisation-python`.
- Configured PyCharm to use the new interpreter.
- Installed `pydantic-settings`.

**Affected location:**
- `.venv/`
- PyCharm interpreter configuration

**Reason:**
- The previously configured Python executable no longer existed.

**Result:**
- The project interpreter and package installation are working.

**Pending:**
- Confirm that the FastAPI application starts correctly.

### 2026-08-07 — GIS Preprocessing Layer Added

**Changed:**
- Added: `app/gis/` and `app/models/` directories.
- Added: Coordinate Reference System (CRS) transformations and GeoJSON extraction.

**Affected files:**
- `app/gis/crs.py`, `app/gis/geojson.py`, `app/gis/geometry.py`, `app/gis/preprocessing.py`, `app/models/spatial.py`

**Reason:**
- The engine needs to translate incoming WGS84 coordinates into metric UTM dataclasses before network graph creation.

**Result:**
- Point extraction and unified project centroid CRS conversion are functioning perfectly and tested.

**Pending:**
- Integration with graph topology generation.

---

## 20. Current Working Features

- Project directory configured in PyCharm.
- Virtual environment created inside `optimisation-python`.
- PyCharm interpreter connected to the new virtual environment.
- FastAPI-related dependencies installed.
- `pydantic-settings` installed successfully.
- **Implemented:** `/health` endpoint and `optimise` request/response schemas.
- **Implemented:** GIS `crs.py` for UTM detection and transformation.
- **Implemented:** GIS `geometry.py` and `geojson.py` for GeoJSON parsing.
- **Implemented:** `preprocessing.py` and strictly typed dataclasses in `app/models/spatial.py`.

---

## 21. Features Currently Under Development

- **Partial:** FastAPI application structure and Endpoints (wiring).
- **Partial:** Environment-based configuration.
- **Planned:** Network graph algorithms and topology mapping.
- **Planned:** Routing algorithms (A*, Dijkstra).
- **Planned:** Machine-learning modules.

---

## 22. Known Limitations

* Route optimisation algorithms: Status: Planned — not implemented
* GIS data source: Status: Planned — not implemented
* API authentication: Status: Planned — not implemented
* ML models: Status: Planned — not implemented
* Java–Python integration: Status: Planned — not implemented
* Automated testing: Status: Planned — not implemented
* Deployment configuration: Status: Planned — not implemented

---

## 23. Current Problems

None currently confirmed.

---

## 24. Next Tasks

1. Verify the selected Python interpreter.
2. Run the FastAPI application.
3. Confirm that the root endpoint responds.
4. Add a health-check endpoint.
5. Finalise the package directory structure.

---

## 25. Important Decisions

Record technical decisions so that they are not repeatedly reconsidered.

### Decision 1: Python Version

**Decision:** Use Python 3.11.

**Reason:** It provides broad compatibility with FastAPI, Pydantic, GIS libraries, optimisation libraries, and machine-learning packages.

### Decision 2: Python API Framework

**Decision:** Use FastAPI.

**Reason:** It provides typed request validation, automatic API documentation, asynchronous support, and easy Java integration through HTTP/JSON.

### Decision 3: Virtual Environment Location

**Decision:** Keep `.venv` inside `optimisation-python`.

**Reason:** This allows PyCharm and developers to locate the project interpreter consistently.

### Decision 4: AI Context File

**Decision:** Maintain one `PROJECT_CONTEXT.md` file.

**Reason:** The same file can be used by Obsidian, Gemini Notebook, NotebookLM, and developers.

Add future architectural decisions below this section.

---

## 26. Commands Reference

### Activate Environment

```bat
.venv\Scripts\activate
```

### Check Python Version

```bat
python --version
```

### Install Dependencies

```bat
pip install -r requirements.txt
```

### Start FastAPI

```bat
uvicorn app.main:app --reload
```

### Open API Documentation

```text
http://127.0.0.1:8000/docs
```

### Run Tests

```bat
pytest
```

### Check Git Changes

```bat
git status
git diff
```

### Commit Changes

```bat
git add -A
git commit -m "Describe the change"
```

---

## 27. Instructions for AI Assistants

When analysing this project:

1. Treat this file as the latest project context.
2. Do not assume that a planned feature has been implemented.
3. Check the **Current Working Features** section before suggesting changes.
4. Preserve the current directory structure unless restructuring is explicitly requested.
5. Use Python 3.11-compatible packages.
6. Keep FastAPI routes, business logic, schemas, and ML logic separated.
7. Never hardcode secrets, passwords, tokens, or API keys.
8. Explain which files must be created or modified.
9. Provide Windows CMD-compatible commands unless another terminal is specified.
10. Consider Java–Python integration when designing API contracts.
11. Update the directory tree when files are added, removed, renamed, or moved.
12. Distinguish between completed work, work in progress, and planned work.
13. Read the **Recent Major Changes**, **Current Problems**, and **Next Tasks** sections before proposing the next implementation step.

---

## 28. Context File Update Checklist

After every major change, update only the relevant items:

* [ ] Last major update
* [ ] Directory structure
* [ ] Important files
* [ ] Dependencies
* [ ] API endpoints
* [ ] Data models and schemas
* [ ] Optimisation pipeline
* [ ] ML pipeline
* [ ] Working features
* [ ] Features under development
* [ ] Known limitations
* [ ] Current problems
* [ ] Next tasks
* [ ] Recent major changes
* [ ] Important decisions
* [ ] Commands, if they changed

Do not rewrite the complete file after every small code edit.

---

## 29. One-Minute Update Format

For a normal major change, update the file using this compact format:

```markdown
### YYYY-MM-DD — Short Change Name

**Changed:**
- Added:
- Modified:
- Removed:

**Affected files:**
- `path/to/file.py`

**Reason:**
- Why the change was made.

**Result:**
- What works now.

**Pending:**
- What remains incomplete.
```

---

## 30. Current Context Summary

**Current stage:** Initial backend setup

**Python version:** Python 3.11.9

**Backend framework:** FastAPI

**Current interpreter:** `.venv\\Scripts\\python.exe`

**Latest completed work:** Recreated and configured the project virtual environment and installed `pydantic-settings`.

**Current blocker:** None confirmed

**Next immediate task:** Start the FastAPI application and verify its endpoints.

**Last updated:** 2026-08-06 21:15 IST

For routine updates, the most important sections are **Current Directory Structure**, **Recent Major Changes**, **Current Working Features**, **Current Problems**, **Next Tasks**, and **Current Context Summary**. You can delete unused sections until those features actually become relevant.
