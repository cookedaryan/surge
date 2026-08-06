# WTG Grouping & Clustering

## Objective
Group $N$ wind turbine generators into $K$ feeder sub-networks such that each feeder current does not exceed conductor ampacity limits and cable length is minimized.

## Approach
- K-Means / Constrained Agglomerative Clustering subject to load capacity limits ($I_{feeder} \le I_{max}$).
- Output feeds into feeder tree topology generation.

---

## Related Notes
- [[Routing]]
- [[Feeder Planning]]
