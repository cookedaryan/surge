# Non-Functional Requirements

## 1. Performance & Scalability
- **NFR-01**: Optimization engine shall produce candidate routes for a 50-WTG wind farm within 30 seconds.
- **NFR-02**: Web GIS map rendering shall maintain 60 FPS performance when displaying up to 10,000 spatial features.

## 2. Reliability & Safety
- **NFR-03**: Routing output must strictly adhere to electrical safety standards (IEC 60826 / IS 5613).
- **NFR-04**: System shall persist all scenario calculation inputs and parameters to allow 100% deterministic reproducibility.

## 3. Usability & Export
- **NFR-05**: Engineering report export (BOM & line schedule) shall execute in under 5 seconds.
