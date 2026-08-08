CREATE EXTENSION IF NOT EXISTS postgis;

CREATE TABLE projects (
    id UUID PRIMARY KEY,
    name VARCHAR(200) NOT NULL,
    description TEXT,
    crs VARCHAR(32) NOT NULL DEFAULT 'EPSG:4326',
    boundary geometry(Polygon, 4326),
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE wtg_locations (
    id UUID PRIMARY KEY,
    project_id UUID NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    external_id VARCHAR(100) NOT NULL,
    capacity_mw NUMERIC(12, 3) NOT NULL CHECK (capacity_mw > 0),
    location geometry(Point, 4326) NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT uk_wtg_locations_project_external_id UNIQUE (project_id, external_id)
);

CREATE INDEX idx_wtg_locations_project_id ON wtg_locations(project_id);
CREATE INDEX idx_wtg_locations_location ON wtg_locations USING GIST(location);

CREATE TABLE substations (
    id UUID PRIMARY KEY,
    project_id UUID NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    external_id VARCHAR(100) NOT NULL,
    capacity_mw NUMERIC(12, 3) CHECK (capacity_mw > 0),
    location geometry(Point, 4326) NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT uk_substations_project_external_id UNIQUE (project_id, external_id)
);

CREATE INDEX idx_substations_project_id ON substations(project_id);
CREATE INDEX idx_substations_location ON substations USING GIST(location);
