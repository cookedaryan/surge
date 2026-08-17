-- The conductors the optimiser is allowed to choose between.
--
-- Until now there was exactly one, and it was fictional. The Python compatibility layer
-- synthesises a single "MVP-COMPATIBILITY-CABLE" whose impedances are placeholders
-- (0.03 ohm/km, 0.10 ohm/km, 200 nF/km) and whose ampacity is back-derived from the feeder
-- capacity typed into the UI. Every electrical figure the system has ever produced -- losses,
-- voltage drop, segment utilisation -- was computed against that one invented conductor, and
-- per-segment cable sizing had nothing to select from.
--
-- data_provenance is the load-bearing column. Conductor parameters that nobody has checked
-- against a supplier datasheet must not be indistinguishable from ones that have been, because
-- the resulting numbers look equally authoritative in a report. It mirrors the land engine's
-- QUOTED / ESTIMATED / UNKNOWN treatment of prices, for the same reason.
CREATE TABLE cable_types (
    id                      UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    cable_type_id           VARCHAR(60)     NOT NULL UNIQUE,
    display_name            VARCHAR(120)    NOT NULL,
    nominal_voltage_kv      NUMERIC(6, 2)   NOT NULL,
    resistance_ohm_per_km   NUMERIC(10, 5)  NOT NULL CHECK (resistance_ohm_per_km >= 0),
    reactance_ohm_per_km    NUMERIC(10, 5)  NOT NULL CHECK (reactance_ohm_per_km >= 0),
    capacitance_nf_per_km   NUMERIC(10, 3)  NOT NULL CHECK (capacitance_nf_per_km >= 0),
    max_current_a           NUMERIC(10, 2)  NOT NULL CHECK (max_current_a > 0),
    parallel_count          INTEGER         NOT NULL DEFAULT 1 CHECK (parallel_count >= 1),
    derating_factor         NUMERIC(4, 3)   NOT NULL DEFAULT 1.000
                                CHECK (derating_factor > 0 AND derating_factor <= 1),
    -- VERIFIED   = checked against a supplier datasheet or utility standard for this project
    -- INDICATIVE = a published typical value, good enough to plan with, not to build from
    -- UNKNOWN    = present for identification only
    data_provenance         VARCHAR(20)     NOT NULL DEFAULT 'UNKNOWN'
                                CHECK (data_provenance IN ('VERIFIED', 'INDICATIVE', 'UNKNOWN')),
    source_note             VARCHAR(300),
    enabled                 BOOLEAN         NOT NULL DEFAULT TRUE,
    created_at              TIMESTAMPTZ     NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at              TIMESTAMPTZ     NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_cable_types_voltage ON cable_types (nominal_voltage_kv, enabled);

-- Seeded with the ACSR conductors ordinarily used on Indian 33 kV distribution, so the optimiser
-- has a real range to size against instead of one invented cable.
--
-- Every row is INDICATIVE. The identities are genuine standard conductors; the electrical values
-- are typical published figures for ACSR at 20 C with representative 33 kV spacing, not readings
-- from the datasheets of the conductor this project will actually buy. Resistance varies with
-- temperature and reactance with tower geometry, so both will differ in practice. They are here
-- so the engine can work, and flagged so nobody mistakes them for verified engineering.
INSERT INTO cable_types (
    cable_type_id, display_name, nominal_voltage_kv,
    resistance_ohm_per_km, reactance_ohm_per_km, capacitance_nf_per_km,
    max_current_a, data_provenance, source_note
) VALUES
    ('ACSR-WEASEL',  'ACSR Weasel (34 mm2)',   33.00, 0.91160, 0.39100,  9.000, 150.00,
     'INDICATIVE', 'Typical published ACSR values; verify against supplier datasheet before use'),
    ('ACSR-RABBIT',  'ACSR Rabbit (55 mm2)',   33.00, 0.54490, 0.37600,  9.300, 185.00,
     'INDICATIVE', 'Typical published ACSR values; verify against supplier datasheet before use'),
    ('ACSR-RACCOON', 'ACSR Raccoon (80 mm2)',  33.00, 0.36560, 0.36500,  9.500, 235.00,
     'INDICATIVE', 'Typical published ACSR values; verify against supplier datasheet before use'),
    ('ACSR-DOG',     'ACSR Dog (105 mm2)',     33.00, 0.27920, 0.35600,  9.700, 290.00,
     'INDICATIVE', 'Typical published ACSR values; verify against supplier datasheet before use'),
    ('ACSR-PANTHER', 'ACSR Panther (212 mm2)', 33.00, 0.13900, 0.33600, 10.200, 470.00,
     'INDICATIVE', 'Typical published ACSR values; verify against supplier datasheet before use');
