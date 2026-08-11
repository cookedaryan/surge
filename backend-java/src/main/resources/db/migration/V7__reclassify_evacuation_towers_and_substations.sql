-- V7: Reclassify any towers or substations previously misclassified as WTGs in wtg_locations.

-- 1. Move evacuation towers (TWR, TOWER, POLE, STR, T-*, AP-*, GANTRY)
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
    COALESCE(w.source_folder, 'reclassified-from-wtg-locations'),
    w.location,
    w.created_at,
    CURRENT_TIMESTAMP
FROM wtg_locations w
WHERE w.external_id ~* '^\d+\s*/\s*\d+(-\d+)?$'
   OR w.external_id ~* '^AP[\s_-]*\d+(-\d+)?$'
   OR w.external_id ~* '^GANTRY(-\d+)?$'
   OR w.external_id ~* '^TOWER[\s_-]*\d+(-\d+)?$'
   OR w.external_id ~* '^TWR[\s_-]*\d+(-\d+)?$'
   OR w.external_id ~* '^POLE[\s_-]*\d+(-\d+)?$'
   OR w.external_id ~* '^STR[\s_-]*\d+(-\d+)?$'
   OR w.external_id ~* '^T[\s_-]*\d+(-\d+)?$'
   OR (w.source_folder IS NOT NULL AND w.source_folder ~* '(tower|twr|gantry|evacuation|transmission|angle point|pole)');

DELETE FROM wtg_locations
WHERE external_id ~* '^\d+\s*/\s*\d+(-\d+)?$'
   OR external_id ~* '^AP[\s_-]*\d+(-\d+)?$'
   OR external_id ~* '^GANTRY(-\d+)?$'
   OR external_id ~* '^TOWER[\s_-]*\d+(-\d+)?$'
   OR external_id ~* '^TWR[\s_-]*\d+(-\d+)?$'
   OR external_id ~* '^POLE[\s_-]*\d+(-\d+)?$'
   OR external_id ~* '^STR[\s_-]*\d+(-\d+)?$'
   OR external_id ~* '^T[\s_-]*\d+(-\d+)?$'
   OR (source_folder IS NOT NULL AND source_folder ~* '(tower|twr|gantry|evacuation|transmission|angle point|pole)');

-- 2. Move substations (PSS, Substation, S/S, SS, SUB, Switchyard)
INSERT INTO substations (id, project_id, external_id, capacity_mw, source_folder, location, created_at, updated_at)
SELECT
    gen_random_uuid(),
    w.project_id,
    w.external_id,
    NULL,
    COALESCE(w.source_folder, 'reclassified-from-wtg-locations'),
    w.location,
    w.created_at,
    CURRENT_TIMESTAMP
FROM wtg_locations w
WHERE (w.external_id ~* '(\mPSS\M|SUBSTATION|SWITCHYARD|\mSS\M|\mSUB\M)'
       OR w.external_id ~* '\d+\s*/\s*\d+\s*KV'
       OR (w.source_folder IS NOT NULL AND w.source_folder ~* '(pss|substation|switchyard|s/s|ss)'))
  AND NOT EXISTS (
        SELECT 1 FROM substations s
        WHERE s.project_id = w.project_id AND s.external_id = w.external_id
  );

DELETE FROM wtg_locations
WHERE external_id ~* '(\mPSS\M|SUBSTATION|SWITCHYARD|\mSS\M|\mSUB\M)'
   OR external_id ~* '\d+\s*/\s*\d+\s*KV'
   OR (source_folder IS NOT NULL AND source_folder ~* '(pss|substation|switchyard|s/s|ss)');
