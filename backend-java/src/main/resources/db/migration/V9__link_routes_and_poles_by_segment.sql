-- Lets a route segment's real pole count be looked up instead of relying on the
-- /150m fallback estimate computed before real pole placement ran.
ALTER TABLE generated_routes ADD COLUMN segment_id VARCHAR(60);
ALTER TABLE generated_poles ADD COLUMN connected_route_ids TEXT[];
