package com.power.surge.dto.client.python;

import com.fasterxml.jackson.annotation.JsonIgnoreProperties;
import com.fasterxml.jackson.annotation.JsonProperty;

/**
 * Contract C2 {@code termination}: why a run stopped.
 *
 * <p>Read as a String for the same reason as the solver status: the reason vocabulary is additive,
 * and a value Java has not heard of must not become a parse failure. The conformance test holds
 * Java to accepting every reason the schema lists.
 *
 * <p>The distinction this block carries is between a run that finished and a run that was stopped.
 * Both return candidates; only one of them searched the space it was asked to.
 */
@JsonIgnoreProperties(ignoreUnknown = true)
public record PythonRunTermination(
        @JsonProperty("reason") String reason,
        @JsonProperty("message") String message
) {
}
