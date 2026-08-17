-- The commercial rates the optimiser needs before it will cost anything at all.
--
-- Python computes conductor CAPEX, pole CAPEX, land cost, loss valuation and a lifecycle total,
-- but only when a request carries a costing_config. Java has never sent one, so every candidate
-- the application has ever received came back with cost: null. Meanwhile the product displays
-- money: the BOM total, the scenario comparison and the route popups all show a figure derived
-- from route length x 80, a constant with no basis and no currency.
--
-- data_provenance is the load-bearing column, for the same reason it is on cable_types. A rate
-- nobody has obtained a quotation for produces a total that looks exactly as authoritative as one
-- that has been tendered. It mirrors the land engine's QUOTED / ESTIMATED / UNKNOWN treatment of
-- prices, and it is per item rather than per catalogue because a project will typically have firm
-- conductor prices long before it has firm land rates.
CREATE TABLE cost_catalogues (
    id                          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    catalogue_id                VARCHAR(60)     NOT NULL UNIQUE,
    version                     VARCHAR(30)     NOT NULL,
    -- ISO 4217. Python validates the length, and every rate below is in this unit; nothing in
    -- the system converts between currencies, so mixing them would silently add rupees to dollars.
    currency                    CHAR(3)         NOT NULL,
    price_basis_date            DATE            NOT NULL,

    -- Land policy. A route crossing someone's field costs something even where no purchase
    -- happens: survey, notice, legal work, crop compensation. The fixed part is per affected
    -- parcel; the variable part is charged on whichever basis the project actually uses.
    land_fixed_cost_per_parcel  NUMERIC(14, 2)  NOT NULL DEFAULT 0
                                    CHECK (land_fixed_cost_per_parcel >= 0),
    land_variable_basis         VARCHAR(30)     NOT NULL DEFAULT 'NONE'
                                    CHECK (land_variable_basis IN (
                                        'NONE', 'ROUTE_OVERLAP_LENGTH_M', 'ROW_INTERSECTION_AREA_M2')),
    land_variable_rate          NUMERIC(14, 4)  NOT NULL DEFAULT 0
                                    CHECK (land_variable_rate >= 0),

    -- Lifecycle valuation. Held on the catalogue rather than a table of its own because a
    -- catalogue version pins the discount rate and energy price it was priced against; quoting a
    -- lifecycle cost from one year's rates against another year's energy price is not comparable.
    analysis_period_years       INTEGER         NOT NULL CHECK (analysis_period_years >= 1),
    discount_rate               NUMERIC(6, 4)   NOT NULL
                                    CHECK (discount_rate >= 0 AND discount_rate < 1),
    annual_operating_hours      INTEGER         NOT NULL
                                    CHECK (annual_operating_hours >= 0 AND annual_operating_hours <= 8760),
    loss_load_factor            NUMERIC(5, 4)   NOT NULL
                                    CHECK (loss_load_factor >= 0 AND loss_load_factor <= 1),
    energy_price_per_mwh        NUMERIC(14, 2)  NOT NULL CHECK (energy_price_per_mwh >= 0),
    energy_price_basis_date     DATE            NOT NULL,

    data_provenance             VARCHAR(20)     NOT NULL DEFAULT 'UNKNOWN'
                                    CHECK (data_provenance IN ('VERIFIED', 'INDICATIVE', 'UNKNOWN')),
    source_note                 VARCHAR(300),
    enabled                     BOOLEAN         NOT NULL DEFAULT TRUE,
    created_at                  TIMESTAMPTZ     NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at                  TIMESTAMPTZ     NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- Conductor rates, keyed on the conductor ids cable sizing actually selects.
--
-- The engine computes length_km x parallel_count x rate, so the rate is for ONE circuit. A twin
-- or quad bundle therefore carries the same rate as its single-circuit parent -- entering a
-- doubled rate for a twin conductor would double the cost twice.
--
-- A conductor the run selects but the catalogue does not cover yields CABLE_COST_NOT_FOUND and no
-- conductor CAPEX and no total, which is correct: the alternative is a total that silently omits
-- the largest line in the estimate.
CREATE TABLE conductor_cost_items (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    catalogue_id        UUID            NOT NULL REFERENCES cost_catalogues (id) ON DELETE CASCADE,
    cable_type_id       VARCHAR(60)     NOT NULL,
    installed_cost_per_km_per_circuit NUMERIC(14, 2) NOT NULL
                            CHECK (installed_cost_per_km_per_circuit >= 0),
    data_provenance     VARCHAR(20)     NOT NULL DEFAULT 'UNKNOWN'
                            CHECK (data_provenance IN ('VERIFIED', 'INDICATIVE', 'UNKNOWN')),
    source_note         VARCHAR(300),
    UNIQUE (catalogue_id, cable_type_id)
);

CREATE TABLE pole_cost_items (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    catalogue_id        UUID            NOT NULL REFERENCES cost_catalogues (id) ON DELETE CASCADE,
    -- Matches the classes the pole placement engine emits, lowercased as Python expects them.
    pole_type           VARCHAR(20)     NOT NULL
                            CHECK (pole_type IN ('terminal', 'angle', 'intermediate', 'junction')),
    installed_cost_each NUMERIC(14, 2)  NOT NULL CHECK (installed_cost_each >= 0),
    data_provenance     VARCHAR(20)     NOT NULL DEFAULT 'UNKNOWN'
                            CHECK (data_provenance IN ('VERIFIED', 'INDICATIVE', 'UNKNOWN')),
    source_note         VARCHAR(300),
    UNIQUE (catalogue_id, pole_type)
);

CREATE INDEX idx_cost_catalogues_enabled ON cost_catalogues (enabled);

-- Seeded so the costing engine can run at all. Every figure is INDICATIVE.
--
-- These are order-of-magnitude rates for Indian 33 kV overhead distribution, in INR, of the kind
-- used for a first-pass estimate. Not one of them is a quotation for this project: conductor and
-- pole erection prices move with steel and aluminium, land rates are intensely local, and the
-- energy price depends on the PPA. They exist so scenarios can be compared against each other,
-- which is a comparison the ranking needs and which survives a uniform error in the rates. They
-- must not be used to commit money.
--
-- Currency is INR because the site and the conductor standards are Indian. Note that the frontend
-- still prints a hardcoded "$" against costs; correcting that is C-2's scope, and until then the
-- symbol shown will be wrong while the number is right.
INSERT INTO cost_catalogues (
    catalogue_id, version, currency, price_basis_date,
    land_fixed_cost_per_parcel, land_variable_basis, land_variable_rate,
    analysis_period_years, discount_rate, annual_operating_hours, loss_load_factor,
    energy_price_per_mwh, energy_price_basis_date,
    data_provenance, source_note
) VALUES (
    'IN-33KV-INDICATIVE', '2026.1', 'INR', '2026-01-01',
    25000.00, 'ROUTE_OVERLAP_LENGTH_M', 400.0000,
    25, 0.0800, 8760, 0.3500,
    3500.00, '2026-01-01',
    'INDICATIVE',
    'First-pass Indian 33 kV rates for scenario comparison only; obtain quotations before committing money'
);

-- One rate per conductor in the cable catalogue. Coverage has to be complete: the run picks the
-- conductor, and any gap costs nothing and voids the total.
INSERT INTO conductor_cost_items (
    catalogue_id, cable_type_id, installed_cost_per_km_per_circuit, data_provenance, source_note
)
SELECT c.id, v.cable_type_id, v.rate, 'INDICATIVE', v.note
FROM cost_catalogues c
CROSS JOIN (VALUES
    ('ACSR-WEASEL',        900000.00, 'Indicative erected cost, 34 mm2 ACSR on 33 kV poles'),
    ('ACSR-RABBIT',       1050000.00, 'Indicative erected cost, 55 mm2 ACSR on 33 kV poles'),
    ('ACSR-RACCOON',      1200000.00, 'Indicative erected cost, 80 mm2 ACSR on 33 kV poles'),
    ('ACSR-DOG',          1350000.00, 'Indicative erected cost, 105 mm2 ACSR on 33 kV poles'),
    ('ACSR-PANTHER',      1800000.00, 'Indicative erected cost, 212 mm2 ACSR on 33 kV poles'),
    -- Bundles take the parent single-circuit rate; the engine multiplies by parallel_count.
    ('ACSR-TWIN-DOG',     1350000.00, 'Per-circuit rate of ACSR Dog; engine multiplies by parallel_count'),
    ('ACSR-TWIN-PANTHER', 1800000.00, 'Per-circuit rate of ACSR Panther; engine multiplies by parallel_count'),
    ('ACSR-QUAD-PANTHER', 1800000.00, 'Per-circuit rate of ACSR Panther; engine multiplies by parallel_count')
) AS v(cable_type_id, rate, note)
WHERE c.catalogue_id = 'IN-33KV-INDICATIVE';

INSERT INTO pole_cost_items (
    catalogue_id, pole_type, installed_cost_each, data_provenance, source_note
)
SELECT c.id, v.pole_type, v.rate, 'INDICATIVE', v.note
FROM cost_catalogues c
CROSS JOIN (VALUES
    ('terminal',     45000.00, 'Indicative erected cost including foundation and stays'),
    ('angle',        38000.00, 'Indicative erected cost including foundation and stays'),
    ('intermediate', 22000.00, 'Indicative erected cost, plain intermediate support'),
    ('junction',     52000.00, 'Indicative erected cost including branch hardware')
) AS v(pole_type, rate, note)
WHERE c.catalogue_id = 'IN-33KV-INDICATIVE';
