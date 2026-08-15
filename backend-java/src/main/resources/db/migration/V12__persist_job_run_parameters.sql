-- Migration V12: make an optimisation job able to describe its own run.
--
-- Feeder capacity, maximum voltage drop and right-of-way width were accepted from the client and
-- forwarded to the optimiser, but never stored. That was survivable only while the pipeline ran
-- inside the request that carried them. Once a job is queued and executed later, anything not on
-- the row is lost -- a run would silently fall back to defaults and quietly ignore the operator's
-- feeder capacity.
--
-- Storing them also makes a completed job reproducible and lets reports state the ROW width that
-- was actually used instead of assuming one.
--
-- Defaults match the API defaults so existing rows describe the run they actually had.

ALTER TABLE optimization_jobs
    ADD COLUMN IF NOT EXISTS feeder_capacity_mw NUMERIC(8, 3) NOT NULL DEFAULT 20.000;

ALTER TABLE optimization_jobs
    ADD COLUMN IF NOT EXISTS max_voltage_drop_pct NUMERIC(5, 2) NOT NULL DEFAULT 5.00;

ALTER TABLE optimization_jobs
    ADD COLUMN IF NOT EXISTS row_width_m NUMERIC(6, 2) NOT NULL DEFAULT 18.00;
