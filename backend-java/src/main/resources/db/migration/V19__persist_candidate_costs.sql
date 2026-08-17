-- Stores the money the engine actually computed.
--
-- Since V18 gave the optimiser rates, every candidate comes back with a full cost breakdown:
-- conductor CAPEX per segment, pole CAPEX per class, land cost, losses valued over the analysis
-- period, and a lifecycle total. None of it was read. Meanwhile every cost in the product came from
-- generated_routes.total_cost, which for a run that reported no cost is route length x 80 -- a
-- constant with no basis, no currency and no provenance.
--
-- Everything here is nullable, and that is the point. A run with no cost catalogue, or one whose
-- catalogue missed a conductor the run selected, has no cost. Nullable means the report can say
-- "not costed" instead of showing a zero that reads as free.

-- Conductor cost is the only component attributable to a single route: the engine emits it per
-- segment. Pole and land costs are computed per pole class and per affected parcel, so splitting
-- them across routes would mean inventing an apportionment the engine never made.
ALTER TABLE generated_routes
    ADD COLUMN conductor_cost NUMERIC(14, 2);

ALTER TABLE optimization_jobs
    -- ISO 4217, carried with the figures because nothing in the system converts currencies and a
    -- number without its unit is not a cost.
    ADD COLUMN cost_currency               CHAR(3),
    ADD COLUMN conductor_capex             NUMERIC(16, 2),
    ADD COLUMN pole_capex                  NUMERIC(16, 2),
    ADD COLUMN land_capex                  NUMERIC(16, 2),
    ADD COLUMN total_capex                 NUMERIC(16, 2),
    -- Losses as energy and as money. The energy figure is what an engineer checks; the money figure
    -- is what makes a longer, lower-loss route comparable to a shorter, lossier one.
    ADD COLUMN annual_loss_energy_mwh      NUMERIC(16, 4),
    ADD COLUMN annual_loss_cost            NUMERIC(16, 2),
    ADD COLUMN present_value_opex          NUMERIC(16, 2),
    ADD COLUMN lifecycle_cost              NUMERIC(16, 2),
    -- Which rates produced these figures. A catalogue can be re-rated afterwards, and a cost read
    -- against different rates from the ones that computed it is not a cost at all.
    ADD COLUMN cost_catalogue_id           VARCHAR(60),
    ADD COLUMN cost_catalogue_version      VARCHAR(30),
    ADD COLUMN cost_price_basis_date       VARCHAR(30),
    -- How many components the engine could not price. Above zero, the totals above are incomplete
    -- by construction: the engine leaves a component null rather than costing a gap at zero, so a
    -- non-zero count is the difference between a total and a partial sum.
    ADD COLUMN cost_failure_count          INTEGER;
