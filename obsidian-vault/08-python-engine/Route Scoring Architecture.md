# Route Scoring Architecture

**Ticket:** SURGE-PY-012 (Legacy) & SURGE-PY-027 (Canonical Unified)  
**Module:** `optimisation-python/app/algorithms/route_scoring.py` & `app/optimisation/scoring.py`  
**Status:** Canonical Unified Scoring Active

---

## Architectural Evolution

> [!note] Evolutionary Status
> - **SURGE-PY-012 (`app/algorithms/route_scoring.py`)** was the initial standalone spatial and constructability scoring engine designed to evaluate alternative network layouts based solely on route length, traversal penalties, parcel counts, road crossings, and pole counts.
> - **SURGE-PY-027 (`app/optimisation/scoring.py`)** is the modern, canonical multi-objective scoring engine. It unifies the spatial constructability criteria of PY-012 with Pandapower AC electrical metrics (PY-015) using canonical metrics (PY-026) and 25-year lifecycle costing (PY-028/029).
> 
> For complete specifications of the production scoring engine, see [[Multi-Objective Candidate Scoring]].

---

## Principles of Cohort-Based Min-Max Scoring

Both the preliminary and canonical scoring engines share foundational mathematical principles regarding multi-criteria decision analysis:

### 1. Cohort Relativity
Normalized scores are inherently relative to the specific cohort of candidates evaluated in a single optimization run. 
- Scores computed in separate optimization runs or across different wind farm sites cannot be compared directly.
- Adding or removing a candidate shifts the cohort min/max boundaries and recalculated scores.

### 2. Normalization Bounds & Benefit Direction
To normalize diverse physical quantities (metres of cable, count of parcels, megawatts of loss) into a dimensionless score in $[0.0, 1.0]$:

$$\text{benefit}(x) = \frac{\max_{\text{cohort}}(x) - x}{\max_{\text{cohort}}(x) - \min_{\text{cohort}}(x)} \quad (\text{for "lower is better"} \text{ metrics})$$

### 3. Constant Range Invariant
If all eligible candidates in a cohort achieve identical performance on a metric ($\max = \min$), the normalized benefit is set to `0.0`. Weights are never artificially shifted between metrics, ensuring deterministic behavior.

### 4. Identity Deduplication of Non-Additive Spatial Metrics
Metrics such as Right-of-Way (ROW) corridor footprint ($m^2$), cadastral parcel intersections, and environmental buffer crossings are **non-additive** across individual route segments. For example, two parallel feeder routes sharing a single road crossing must count as 1 road crossing event, not 2. Deduplication must be resolved at the network level prior to cohort scoring.

### 5. Exclusionary Hard Violations
Candidates that intersect hard restricted zones or fail electrical limits are flagged as infeasible (`feasible = False`):
- Infeasible candidates are excluded from cohort min/max normalization bounds to prevent skewing the scale for valid designs.
- Infeasible candidates receive a `None` score and cannot be selected as the recommended design.
- Diagnostic violation codes are preserved for user explainability.

---

## Legacy Scorer Model (`app/algorithms/route_scoring.py`)

The standalone PY-012 scorer evaluates `NetworkCandidateMetrics`:

```python
@dataclass(frozen=True)
class NetworkCandidateMetrics:
    candidate_id: str
    total_length_m: float
    total_traversal_cost: float
    affected_parcel_count: int
    road_crossing_count: int
    soft_constraint_overlap_length_m: float
    environmental_area_overlap_m2: float
    generated_pole_record_count: int
    hard_violation_ids: tuple[str, ...] = ()
```

*(This module is maintained in `app/algorithms/` for algorithmic regression testing; production orchestration invokes `app/optimisation/scoring.py`).*

---

## Related Notes

- [[Multi-Objective Candidate Scoring]]
- [[Canonical Candidate Engineering Metrics]]
- [[Candidate PNC Scenario Generation]]
- [[Surge MVP Ticket Plan]]
- [[Overview & Layout]]
