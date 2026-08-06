# Explainable AI (XAI) Engineering Decisions

## Rationale
Engineers must understand *why* a particular route or pole placement was selected.

## Explanations Generated
1. **Route Penalty Breakdown**: Shows cost contribution from slope, road proximity, forest avoidance, and land compensation.
2. **Pole Selection Rationale**: Explains why tension poles were chosen over suspension poles (e.g. angle change $> 15^\circ$ or span length $> 200m$).
3. **Trade-off Analysis**: Compares selected route against 3 rejected alternative candidate paths.

---

## Related Notes
- [[Routing]]
- [[Cost Model]]
- [[ML Ranking]]
