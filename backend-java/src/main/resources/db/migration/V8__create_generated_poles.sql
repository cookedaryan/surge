CREATE TABLE generated_poles (
    id UUID PRIMARY KEY,
    job_id UUID NOT NULL REFERENCES optimization_jobs(id) ON DELETE CASCADE,
    pole_identifier VARCHAR(150) NOT NULL,
    feeder_name VARCHAR(100),
    pole_role VARCHAR(30),
    recommended_pole_type VARCHAR(100),
    connected_feeder_ids TEXT[],
    location geometry(Point, 4326) NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_generated_poles_job_id ON generated_poles(job_id);
CREATE INDEX idx_generated_poles_location ON generated_poles USING GIST(location);
