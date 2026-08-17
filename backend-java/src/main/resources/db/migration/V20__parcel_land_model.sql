ALTER TABLE cadastral_parcels
    ADD COLUMN owner_id UUID,
    ADD COLUMN availability_status VARCHAR(50) DEFAULT 'UNKNOWN',
    ADD COLUMN transaction_mode VARCHAR(50),
    ADD COLUMN price_status VARCHAR(50) DEFAULT 'UNKNOWN',
    ADD COLUMN price_date VARCHAR(30);

