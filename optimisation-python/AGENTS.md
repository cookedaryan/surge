# Agent Directives for SURGE Python Service

1. **Scope Limit:** Only edit files under `app/` and `tests/`. Do not alter root infrastructure without explicit prompt instruction.
2. **Type Safety:** Maintain strict typing. Run `mypy .` on all changes; zero type errors allowed.
3. **Linting:** Code must pass `ruff check .` and formatting standards.
4. **Testing:** Write corresponding unit tests in `tests/` for any new logic or endpoint. Ensure `pytest` passes before completing tasks.
5. **Geospatial Integrity**
   - GeoJSON API input and output must use RFC 7946 WGS84
     coordinates in longitude-latitude order.
   - Before calculating distance, area, buffers, routing costs,
     or right-of-way widths, transform geometries to a suitable
     projected metre-based CRS.
   - Never calculate metre-based distances directly from
     longitude and latitude degrees.
   - Transform final results back to WGS84 before exporting GeoJSON.