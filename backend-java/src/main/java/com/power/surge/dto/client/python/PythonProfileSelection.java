package com.power.surge.dto.client.python;

import com.fasterxml.jackson.annotation.JsonProperty;

/**
 * Contract C1 {@code OptimisationRequest.profile}: an allow-listed profile ID and version.
 *
 * <p>Serialises to {@code contracts/fixtures/request/profile-selection.json} exactly — two string
 * fields, nothing else. The schema sets {@code additionalProperties: false}, so an extra field here
 * would be rejected by Python rather than ignored.
 *
 * <p>Only {@link com.power.surge.service.OptimisationProfile} should build one, so a value that was
 * never allow-listed cannot reach the wire.
 */
public record PythonProfileSelection(
        @JsonProperty("id") String id,
        @JsonProperty("version") String version
) {
}
