package com.power.surge.dto.client.python;

import com.fasterxml.jackson.annotation.JsonIgnoreProperties;
import com.fasterxml.jackson.annotation.JsonProperty;

import java.util.List;
import java.util.Map;

/**
 * Contract C2 {@code search_evidence}: what the bounded search actually did.
 *
 * <p>{@code caps} and {@code counts} are read as maps rather than as records with a field per key.
 * The contract fixes their key sets and the conformance test checks Java against the schema's list,
 * which is a stronger check than a Java record could give: a record only proves Java agrees with
 * its own copy of the names, while the map plus the schema proves it agrees with the contract. It
 * also means a CCR adding a counter reaches Java as data instead of being silently dropped.
 *
 * <p>Absent unless search is enabled (C2 blocks are absent when not produced), so today this is
 * always null. WP4-7 is what fills it, and slot 3 waits on G2.
 */
@JsonIgnoreProperties(ignoreUnknown = true)
public record PythonSearchEvidence(
        @JsonProperty("enabled") Boolean enabled,
        @JsonProperty("caps") Map<String, Integer> caps,
        @JsonProperty("counts") Map<String, Integer> counts,
        @JsonProperty("lineage") List<LineageEntry> lineage,
        @JsonProperty("routing_time_s") Double routingTimeS,
        @JsonProperty("admission_deadline_s") Double admissionDeadlineS,
        @JsonProperty("admission_deadline_reached") Boolean admissionDeadlineReached
) {

    /** Where one candidate came from: its parent, the mutation, and whether it was a duplicate. */
    @JsonIgnoreProperties(ignoreUnknown = true)
    public record LineageEntry(
            @JsonProperty("candidate_id") String candidateId,
            @JsonProperty("parent_id") String parentId,
            @JsonProperty("round") Integer round,
            @JsonProperty("mutation_type") String mutationType,
            @JsonProperty("discarded_duplicate_of") String discardedDuplicateOf
    ) {
    }
}
