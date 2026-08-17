-- Records which conductor the optimiser selected for each route segment.
--
-- The engine has sized cables per segment since PY-030 and reported the result on every candidate,
-- but nothing outside Python read it. Conductor is a bill-of-materials line item and the single
-- biggest material cost in a collector network, so a BOM that omits it is not costable.
--
-- Utilisation is stored alongside the type because the type alone does not say whether the choice
-- is comfortable or marginal: a segment at 98% of its effective ampacity is a different
-- engineering proposition from one at 40%, and only the percentage distinguishes them.
--
-- Nullable throughout: jobs that ran before this, and any run where sizing did not report a
-- segment, keep a null rather than a fabricated default.
ALTER TABLE generated_routes
    ADD COLUMN cable_type_id VARCHAR(100),
    ADD COLUMN cable_required_current_a NUMERIC(10, 2),
    ADD COLUMN cable_effective_ampacity_a NUMERIC(10, 2),
    ADD COLUMN cable_utilisation_pct NUMERIC(6, 2);
