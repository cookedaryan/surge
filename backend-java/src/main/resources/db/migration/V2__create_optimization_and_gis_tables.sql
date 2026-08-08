CREATE TABLE cadastral_parcels (
    id UUID PRIMARY KEY,
    project_id UUID NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    parcel_id VARCHAR(100) NOT NULL,
    owner_name VARCHAR(200),
    acquisition_cost_per_m2 NUMERIC(14, 2) CHECK (acquisition_cost_per_m2 >= 0),
    geometry geometry(Polygon, 4326) NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT uk_cadastral_parcels_project_parcel_id UNIQUE (project_id, parcel_id)
);

CREATE INDEX idx_cadastral_parcels_project_id ON cadastral_parcels(project_id);
CREATE INDEX idx_cadastral_parcels_geometry ON cadastral_parcels USING GIST(geometry);

CREATE TABLE restricted_areas (
    id UUID PRIMARY KEY,
    project_id UUID NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    name VARCHAR(150) NOT NULL,
    restriction_type VARCHAR(50) NOT NULL,
    buffer_meters NUMERIC(8, 2) NOT NULL DEFAULT 0.0 CHECK (buffer_meters >= 0),
    geometry geometry(Polygon, 4326) NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_restricted_areas_project_id ON restricted_areas(project_id);
CREATE INDEX idx_restricted_areas_geometry ON restricted_areas USING GIST(geometry);

CREATE TABLE optimization_jobs (
    id UUID PRIMARY KEY,
    project_id UUID NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    status VARCHAR(32) NOT NULL DEFAULT 'PENDING',
    algorithm_type VARCHAR(50) NOT NULL DEFAULT 'MULTI_OBJECTIVE_A_STAR',
    capex_weight NUMERIC(5, 4) NOT NULL DEFAULT 0.5000 CHECK (capex_weight >= 0 AND capex_weight <= 1),
    losses_weight NUMERIC(5, 4) NOT NULL DEFAULT 0.5000 CHECK (losses_weight >= 0 AND losses_weight <= 1),
    max_span_meters NUMERIC(8, 2) NOT NULL DEFAULT 150.00 CHECK (max_span_meters > 0),
    voltage_kv NUMERIC(6, 2) NOT NULL DEFAULT 33.00 CHECK (voltage_kv > 0),
    error_message TEXT,
    result_summary_json TEXT,
    started_at TIMESTAMPTZ,
    completed_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_optimization_jobs_project_id ON optimization_jobs(project_id);
CREATE INDEX idx_optimization_jobs_status ON optimization_jobs(status);

CREATE TABLE generated_routes (
    id UUID PRIMARY KEY,
    job_id UUID NOT NULL REFERENCES optimization_jobs(id) ON DELETE CASCADE,
    feeder_name VARCHAR(100) NOT NULL,
    total_length_meters NUMERIC(12, 3) NOT NULL CHECK (total_length_meters >= 0),
    total_cost NUMERIC(14, 2) CHECK (total_cost >= 0),
    electrical_losses_kw NUMERIC(10, 3) CHECK (electrical_losses_kw >= 0),
    pole_count INTEGER NOT NULL DEFAULT 0 CHECK (pole_count >= 0),
    route_path geometry(LineString, 4326) NOT NULL,
    pole_locations geometry(MultiPoint, 4326),
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_generated_routes_job_id ON generated_routes(job_id);
CREATE INDEX idx_generated_routes_path ON generated_routes USING GIST(route_path);
