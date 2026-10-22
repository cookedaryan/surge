-- Records which scoring policy actually produced a job's recommendation (contracts C2, C9 V23).
--
-- Until now a job stored its scenario label and nothing about the policy behind the ranking. That
-- was adequate while every run used the one built-in scoring rule. With profiles, two runs of the
-- same project under the same scenario label can recommend different designs, and afterwards there
-- was no way to say why — the numbers were reproducible only if you happened to know which
-- definitions were deployed on the day.
--
-- Every column is nullable, and NULL has one specific meaning: recorded before this contract
-- existed. It never means "false" and never means "no profile was requested". A reader that treats
-- a NULL profiles_enabled as false would report every historical job as having run with profiles
-- off, which is a claim this table cannot support.
--
-- Expand only: columns are added, nothing is renamed or dropped, so a running deployment reads and
-- writes rows through the change.

ALTER TABLE optimization_jobs
    -- The profile in force. Written when the job is created, from the allow-listed ID the client
    -- asked for, and confirmed from the engine's effective_profile echo when the run returns.
    -- Python fails a run rather than substituting a different profile, so the two agree or the job
    -- does not complete.
    ADD COLUMN profile_id               VARCHAR(64),
    ADD COLUMN profile_version          VARCHAR(16),
    -- The three hashes that make a ranking reproducible. policy_hash covers the resolved weights
    -- and ranges; definition_hash covers the whole definition set and is the value the startup
    -- handshake compares; generation_settings_hash covers what the profile asked the generator for.
    ADD COLUMN policy_hash              CHAR(64),
    ADD COLUMN definition_hash          CHAR(64),
    -- Not covered by the hashes above: the metric registry can move without any policy moving, as
    -- it did in CCR #44, and a cached evaluation from before that bump is not comparable with one
    -- from after it.
    ADD COLUMN metric_registry_version  VARCHAR(16),
    ADD COLUMN generation_settings_hash CHAR(64),
    -- Both flags as the engine reported them, not as this service believes them to be. They are
    -- what distinguishes a V0 run from a profiled one when the profile columns are empty.
    ADD COLUMN profiles_enabled         BOOLEAN,
    ADD COLUMN search_enabled           BOOLEAN;
