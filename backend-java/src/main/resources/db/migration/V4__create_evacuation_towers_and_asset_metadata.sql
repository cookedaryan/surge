-- V4: Evacuation tower assets and provenance metadata for imported point assets.
--
-- Context: KMZ survey exports contain transmission/evacuation line towers alongside turbines.
-- Prior to this migration every imported placemark was persisted into wtg_locations, which both
-- corrupted the optimiser input and forced a fabricated capacity onto non-generating assets.
-- Towers get their own table precisely because wtg_locations.capacity_mw is NOT NULL.

CREATE TABLE evacuation_towers (
    id UUID PRIMARY KEY,
    project_id UUID NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    external_id VARCHAR(100) NOT NULL,
    tower_type VARCHAR(50),
    height_m NUMERIC(8, 2) CHECK (height_m > 0),
    line_section VARCHAR(100),
    source_folder VARCHAR(255),
    location geometry(Point, 4326) NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT uk_evacuation_towers_project_external_id UNIQUE (project_id, external_id)
);

CREATE INDEX idx_evacuation_towers_project_id ON evacuation_towers(project_id);
CREATE INDEX idx_evacuation_towers_location ON evacuation_towers USING GIST(location);

-- Turbine lifecycle status. Survey files carry the micro-siting decision in the KML folder name
-- (Approved / Cancel Location / Low AEP / ...), not in ExtendedData. Only optimisable statuses are
-- sent to the Python engine, so cancelled locations no longer distort feeder grouping.
-- Backfill existing rows as APPROVED so projects already in the system keep working, then flip the
-- column default to UNKNOWN so anything imported from here on must be classified explicitly.
ALTER TABLE wtg_locations
    ADD COLUMN status VARCHAR(32) NOT NULL DEFAULT 'APPROVED',
    ADD COLUMN source_folder VARCHAR(255);

ALTER TABLE wtg_locations
    ALTER COLUMN status SET DEFAULT 'UNKNOWN';

ALTER TABLE wtg_locations
    ADD CONSTRAINT ck_wtg_locations_status CHECK (
        status IN ('APPROVED', 'REGISTRATION', 'PROPOSED', 'TO_BE_SHIFTED',
                   'LOW_AEP', 'CANCELLED', 'UNKNOWN')
    );

CREATE INDEX idx_wtg_locations_status ON wtg_locations(project_id, status);

ALTER TABLE substations
    ADD COLUMN source_folder VARCHAR(255);

COMMENT ON COLUMN wtg_locations.status IS
    'Micro-siting lifecycle status derived from the KML source folder. Only APPROVED, REGISTRATION and PROPOSED feed the optimiser.';
COMMENT ON COLUMN wtg_locations.source_folder IS
    'KML folder path the placemark was imported from. Retained for audit and re-classification.';
COMMENT ON TABLE evacuation_towers IS
    'Existing transmission/evacuation line towers, angle points and gantries. Reference assets: rendered and stored, excluded from collector-network optimisation.';
