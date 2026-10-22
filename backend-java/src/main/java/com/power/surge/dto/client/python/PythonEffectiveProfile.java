package com.power.surge.dto.client.python;

import com.fasterxml.jackson.annotation.JsonIgnoreProperties;
import com.fasterxml.jackson.annotation.JsonProperty;

/**
 * Contract C2 {@code effective_profile}: the policy and flag state behind one response.
 *
 * <p>Absent when neither profiles nor search are enabled, which is every run the product makes
 * today — C2 blocks are absent when not produced, so a null here is a V0 run and not an error.
 *
 * <p>{@code profile_id} and the three hashes are nullable within the block too: a run with profiles
 * switched on but no profile requested still reports the flags and the metric registry version.
 * Both flags are primitives in the contract and required, so they are read as {@code Boolean} only
 * to survive a malformed body without a parse failure that would read like a policy error.
 */
@JsonIgnoreProperties(ignoreUnknown = true)
public record PythonEffectiveProfile(
        @JsonProperty("profile_id") String profileId,
        @JsonProperty("profile_version") String profileVersion,
        @JsonProperty("policy_hash") String policyHash,
        @JsonProperty("definition_hash") String definitionHash,
        @JsonProperty("metric_registry_version") String metricRegistryVersion,
        @JsonProperty("generation_settings_hash") String generationSettingsHash,
        @JsonProperty("profiles_enabled") Boolean profilesEnabled,
        @JsonProperty("search_enabled") Boolean searchEnabled
) {
}
