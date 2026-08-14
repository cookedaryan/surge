-- Lets the scenario comparison report look up real completed jobs per scenario instead of
-- fabricating numbers, since the scenario the user picked was previously never persisted.
ALTER TABLE optimization_jobs ADD COLUMN scenario VARCHAR(60);
