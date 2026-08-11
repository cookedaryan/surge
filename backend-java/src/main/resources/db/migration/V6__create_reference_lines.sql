-- V6: Linear reference features imported from survey KMZ files.
--
-- Roads, HT/EHV lines, watercourses and previously proposed evacuation routes are existing site
-- features. They are NOT restricted areas: a corridor crosses a road or an HT line at a cost
-- (clearance, permitting, a crossing structure), whereas a restricted area must be avoided
-- entirely. Modelling them as exclusions would make the router refuse to cross a highway, which
-- would distort every route in the project.
--
-- Before this migration the importer discarded LineString placemarks outright — 134 of them in the
-- reference Uravakonda file, including NH-42, SH-42, the 133 KV line and the estimated PCN route.

CREATE TABLE reference_lines (
    id UUID PRIMARY KEY,
    project_id UUID NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    external_id VARCHAR(150) NOT NULL,
    line_type VARCHAR(32) NOT NULL,
    -- Cost applied when a routed corridor crosses this feature. NULL means "use the project
    -- default for this line type"; populated once PY-008 cost surfacing lands.
    crossing_cost NUMERIC(14, 2) CHECK (crossing_cost >= 0),
    voltage_kv NUMERIC(8, 2) CHECK (voltage_kv > 0),
    length_m NUMERIC(14, 2) CHECK (length_m >= 0),
    source_folder VARCHAR(255),
    path geometry(LineString, 4326) NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT ck_reference_lines_type CHECK (
        line_type IN ('ROAD', 'HT_LINE', 'EVACUATION_ROUTE', 'WATERCOURSE', 'MEASUREMENT', 'UNKNOWN')
    )
);

CREATE INDEX idx_reference_lines_project_id ON reference_lines(project_id);
CREATE INDEX idx_reference_lines_path ON reference_lines USING GIST(path);
CREATE INDEX idx_reference_lines_type ON reference_lines(project_id, line_type);

-- Survey files repeat names constantly ("Path Measure" appears dozens of times), so external_id is
-- deliberately NOT unique per project. Deduplication happens on geometry during import instead.

COMMENT ON TABLE reference_lines IS
    'Existing linear site features - roads, HT/EHV lines, watercourses, prior routes. Reference and crossing-cost inputs; not SURGE output and not exclusion zones.';
COMMENT ON COLUMN reference_lines.line_type IS
    'ROAD, HT_LINE and WATERCOURSE are crossing constraints. EVACUATION_ROUTE is context only.';

-- Provenance for polygons, matching the columns added to the point tables in V4.
ALTER TABLE cadastral_parcels ADD COLUMN IF NOT EXISTS source_folder VARCHAR(255);
ALTER TABLE restricted_areas  ADD COLUMN IF NOT EXISTS source_folder VARCHAR(255);
