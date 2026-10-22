package com.power.surge.dto.client.python;

import com.fasterxml.jackson.annotation.JsonIgnoreProperties;
import com.fasterxml.jackson.annotation.JsonProperty;

/**
 * Contract C7: the body of {@code GET /api/v1/profiles/definition-hash}.
 *
 * <p>Only {@code definition_hash} is compared. Java has no configured expectation for the other
 * two, and inventing one would fail startup over a change the definition hash already covers or
 * does not care about — the metric registry version moved in CCR #44 without any policy moving.
 * They are carried so the startup log can say which build it shook hands with.
 */
@JsonIgnoreProperties(ignoreUnknown = true)
public record PythonDefinitionHashResponse(
        @JsonProperty("definition_hash") String definitionHash,
        @JsonProperty("metric_registry_version") String metricRegistryVersion,
        @JsonProperty("contract_pack_version") String contractPackVersion
) {
}
