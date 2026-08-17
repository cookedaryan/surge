-- Add twin bundle options so the optimiser has more headroom to repair heavy feeders or long voltage drops.
INSERT INTO cable_types (
    cable_type_id, display_name, nominal_voltage_kv,
    resistance_ohm_per_km, reactance_ohm_per_km, capacitance_nf_per_km,
    max_current_a, parallel_count, derating_factor, data_provenance, source_note
) VALUES
    ('ACSR-TWIN-DOG',     'Twin ACSR Dog (2x 105 mm2)',     33.00, 0.27920, 0.35600,  9.700, 290.00, 2, 1.000,
     'INDICATIVE', 'Typical published ACSR values, bundled; verify against supplier datasheet before use'),
    ('ACSR-TWIN-PANTHER', 'Twin ACSR Panther (2x 212 mm2)', 33.00, 0.13900, 0.33600, 10.200, 470.00, 2, 1.000,
     'INDICATIVE', 'Typical published ACSR values, bundled; verify against supplier datasheet before use');
