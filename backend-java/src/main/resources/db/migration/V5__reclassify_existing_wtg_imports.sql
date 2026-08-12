-- V5: Repair assets that were imported before classification existed.
--
-- V4 added the evacuation_towers table and the classification pipeline, but it only affects NEW
-- imports. Every placemark imported before it -- towers, substations and geotechnical markers alike
-- -- is still sitting in wtg_locations, so the map keeps drawing them as turbines and the optimiser
-- keeps consuming them. This migration reclassifies those rows in place.
--
-- Classification here is by external_id only: pre-V4 rows have no source_folder, so the KML folder
-- signal is unavailable. The ID patterns mirror AssetClassificationRules.defaults().
--
-- The trailing '-<n>' alternative in each pattern matches the suffixes the old importer appended
-- when it hit a duplicate name (GANTRY, GANTRY-1, GANTRY-2 ...). Survey KMZ files repeat their own
-- folder tree, so those suffixed rows are numerous.

-- --------------------------------------------------------------------------
-- 1. Move evacuation towers: "<section>/<index>", angle points, gantries.
-- --------------------------------------------------------------------------
INSERT INTO evacuation_towers (
    id, project_id, external_id, tower_type, line_section, source_folder, location, created_at, updated_at
)
SELECT
    gen_random_uuid(),
    w.project_id,
    w.external_id,
    CASE
        WHEN w.external_id ~* '^GANTRY(-\d+)?$'            THEN 'GANTRY'
        WHEN w.external_id ~* '^AP[\s_-]*\d+(-\d+)?$'      THEN 'ANGLE_POINT'
        ELSE 'SUSPENSION'
    END,
    substring(w.external_id from '^(\d+)\s*/'),
    'reclassified-from-wtg-locations',
    w.location,
    w.created_at,
    CURRENT_TIMESTAMP
FROM wtg_locations w
WHERE w.external_id ~* '^\d+\s*/\s*\d+(-\d+)?$'
   OR w.external_id ~* '^AP[\s_-]*\d+(-\d+)?$'
   OR w.external_id ~* '^GANTRY(-\d+)?$'
   OR w.external_id ~* '^TOWER[\s_-]*\d+(-\d+)?$';

DELETE FROM wtg_locations
WHERE external_id ~* '^\d+\s*/\s*\d+(-\d+)?$'
   OR external_id ~* '^AP[\s_-]*\d+(-\d+)?$'
   OR external_id ~* '^GANTRY(-\d+)?$'
   OR external_id ~* '^TOWER[\s_-]*\d+(-\d+)?$';

-- --------------------------------------------------------------------------
-- 2. Move substations: "... PSS", "... Substation", voltage classes like 220/11KV.
--    Guarded against colliding with a substation of the same name already present.
-- --------------------------------------------------------------------------
INSERT INTO substations (id, project_id, external_id, capacity_mw, source_folder, location, created_at, updated_at)
SELECT
    gen_random_uuid(),
    w.project_id,
    w.external_id,
    NULL,
    'reclassified-from-wtg-locations',
    w.location,
    w.created_at,
    CURRENT_TIMESTAMP
FROM wtg_locations w
WHERE (w.external_id ~* '(\mPSS\M|SUBSTATION|SWITCHYARD)'
       OR w.external_id ~* '\d+\s*/\s*\d+\s*KV')
  AND NOT EXISTS (
        SELECT 1 FROM substations s
        WHERE s.project_id = w.project_id AND s.external_id = w.external_id
  );

DELETE FROM wtg_locations
WHERE external_id ~* '(\mPSS\M|SUBSTATION|SWITCHYARD)'
   OR external_id ~* '\d+\s*/\s*\d+\s*KV';

-- --------------------------------------------------------------------------
-- 3. Drop geotechnical survey markers. They are not electrical assets and SURGE does not
--    persist them: boreholes, CBR, ERT, plate load and thermal resistivity tests.
-- --------------------------------------------------------------------------
DELETE FROM wtg_locations
WHERE external_id ~* '^(BH|CBR|ERT|PLT|TP|TRT)[\s_-]*\d+(-\d+)?$';

-- --------------------------------------------------------------------------
-- 4. Collapse the duplicate rows the old importer created.
--    A survey KMZ nests a copy of its own tree, so the same asset was persisted several times
--    under suffixed IDs (KS67_S1, KS67_S1-1, KS67_S1-2) at identical coordinates. Keep the row
--    with the shortest -- i.e. unsuffixed -- external_id.
-- --------------------------------------------------------------------------
-- The duplicate suffix must be stripped BEFORE the separators, otherwise "KS67_S1-2" normalises to
-- "KS67S12" and never matches "KS67S1".
CREATE OR REPLACE FUNCTION surge_asset_key(external_id TEXT) RETURNS TEXT AS $$
    SELECT upper(regexp_replace(regexp_replace($1, '-\d+$', ''), '[\s_.-]', '', 'g'));
$$ LANGUAGE SQL IMMUTABLE;

DELETE FROM wtg_locations w
USING wtg_locations keep
WHERE w.project_id = keep.project_id
  AND ST_Equals(w.location, keep.location)
  AND surge_asset_key(w.external_id) = surge_asset_key(keep.external_id)
  AND (length(w.external_id) > length(keep.external_id)
       OR (length(w.external_id) = length(keep.external_id) AND w.id > keep.id));

DELETE FROM evacuation_towers t
USING evacuation_towers keep
WHERE t.project_id = keep.project_id
  AND ST_Equals(t.location, keep.location)
  AND surge_asset_key(t.external_id) = surge_asset_key(keep.external_id)
  AND (length(t.external_id) > length(keep.external_id)
       OR (length(t.external_id) = length(keep.external_id) AND t.id > keep.id));

DELETE FROM substations s
USING substations keep
WHERE s.project_id = keep.project_id
  AND ST_Equals(s.location, keep.location)
  AND upper(s.external_id) = upper(keep.external_id)
  AND s.id > keep.id;

DROP FUNCTION surge_asset_key(TEXT);

-- --------------------------------------------------------------------------
-- 5. Anything left that does not look like a turbine could not be identified from its ID alone.
--    V4 backfilled every pre-existing row as APPROVED; demote these to UNKNOWN so they are shown
--    on the map but kept out of the optimiser until a human confirms what they are.
-- --------------------------------------------------------------------------
UPDATE wtg_locations
SET status = 'UNKNOWN'
WHERE external_id !~* '^(KS|SUR|VAJ)[\s_-]*\d+'
  AND status = 'APPROVED'
  AND source_folder IS NULL;

-- Turbine micro-siting status (Approved / Cancel Location / Low AEP / ...) lives in the KML folder
-- name and cannot be recovered from the database. Rows reclassified here keep whatever V4 assigned.
-- Re-importing the source KMZ through /assets/kmz/preview is the only way to restore true statuses.
