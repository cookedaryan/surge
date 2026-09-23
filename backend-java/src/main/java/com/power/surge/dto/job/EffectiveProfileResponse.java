package com.power.surge.dto.job;

import com.power.surge.domain.OptimizationJob;

/**
 * What policy produced a job's recommendation, as the browser reads it (contract C2).
 *
 * <p>Field names are camelCase because this is Java's own API, which is camelCase throughout; the
 * snake_case spelling belongs to the engine's contract and stops at
 * {@link com.power.surge.dto.client.python.PythonEffectiveProfile}. The values are unchanged.
 *
 * <p>Absent from a job response when the job has none recorded, which means one of two things and
 * deliberately does not distinguish them here: the job ran before this contract existed, or it ran
 * with both flags off. {@code profilesEnabled} tells them apart — null for the first, false for the
 * second.
 */
public record EffectiveProfileResponse(
        String profileId,
        String profileVersion,
        String policyHash,
        String definitionHash,
        String metricRegistryVersion,
        String generationSettingsHash,
        Boolean profilesEnabled,
        Boolean searchEnabled
) {

    /** The recorded policy, or {@code null} when the job has none. */
    public static EffectiveProfileResponse fromEntity(OptimizationJob job) {
        // The flags are the test, not the profile ID: a run with profiles on and no profile
        // requested has a null ID and is still a run whose policy state was recorded.
        if (job.getProfilesEnabled() == null && job.getSearchEnabled() == null
                && job.getProfileId() == null && job.getMetricRegistryVersion() == null) {
            return null;
        }
        return new EffectiveProfileResponse(
                job.getProfileId(),
                job.getProfileVersion(),
                job.getPolicyHash(),
                job.getDefinitionHash(),
                job.getMetricRegistryVersion(),
                job.getGenerationSettingsHash(),
                job.getProfilesEnabled(),
                job.getSearchEnabled()
        );
    }
}
