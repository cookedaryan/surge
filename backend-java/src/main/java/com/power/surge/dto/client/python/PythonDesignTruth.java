package com.power.surge.dto.client.python;

import com.fasterxml.jackson.annotation.JsonIgnoreProperties;
import com.fasterxml.jackson.annotation.JsonProperty;

import java.util.List;

/**
 * Contract C2 {@code design_truth}: what was actually installed, as opposed to what was first sized.
 *
 * <p>The distinction matters because the engine repairs a candidate after sizing it — a segment
 * that failed a voltage check is upgraded — and until this block existed the only conductor Java
 * stored was the <em>initial</em> choice (finding F3). A bill of materials built from that is a bill
 * for cable nobody installs. WP6A-6 is what moves {@code generated_routes.cable_type_id} onto
 * {@code segments[].final_cable_type_id}; this type is what lets it.
 */
@JsonIgnoreProperties(ignoreUnknown = true)
public record PythonDesignTruth(
        @JsonProperty("candidate_id") String candidateId,
        /** {@code INITIAL_ONLY} or {@code FINAL_INSTALLED}: whether the sizing below was repaired. */
        @JsonProperty("candidate_sizing_basis") String candidateSizingBasis,
        @JsonProperty("repair_actions") List<RepairAction> repairActions,
        @JsonProperty("segments") List<InstalledSegment> segments
) {

    /** One upgrade the engine made, and why. */
    @JsonIgnoreProperties(ignoreUnknown = true)
    public record RepairAction(
            @JsonProperty("segment_id") String segmentId,
            @JsonProperty("repair_iteration") Integer repairIteration,
            @JsonProperty("reason_code") String reasonCode,
            @JsonProperty("trigger_violation_type") String triggerViolationType,
            @JsonProperty("original_cable_type_id") String originalCableTypeId,
            @JsonProperty("upgraded_cable_type_id") String upgradedCableTypeId
    ) {
    }

    /** One segment as built: both conductors, and whether the second differs from the first. */
    @JsonIgnoreProperties(ignoreUnknown = true)
    public record InstalledSegment(
            @JsonProperty("segment_id") String segmentId,
            @JsonProperty("feeder_id") String feederId,
            @JsonProperty("initial_cable_type_id") String initialCableTypeId,
            @JsonProperty("final_cable_type_id") String finalCableTypeId,
            @JsonProperty("repaired") Boolean repaired
    ) {
    }
}
