-- Add quad bundle options so the optimiser has extreme headroom for very long/heavy feeders.
INSERT INTO cable_types (
    cable_type_id, display_name, nominal_voltage_kv,
    resistance_ohm_per_km, reactance_ohm_per_km, capacitance_nf_per_km,
    max_current_a, parallel_count, derating_factor, data_provenance, source_note
) VALUES
    ('ACSR-QUAD-PANTHER', 'Quad ACSR Panther (4x 212 mm2)', 33.00, 0.13900, 0.33600, 10.200, 470.00, 4, 1.000,
     'INDICATIVE', 'Quad bundle added for extreme headroom; verify against supplier datasheet before use');
