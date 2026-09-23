package com.power.surge.dto.client.python;

import com.fasterxml.jackson.annotation.JsonIgnoreProperties;
import com.fasterxml.jackson.annotation.JsonProperty;

import java.util.List;

/**
 * Contract C2 {@code scoring_explanation}: why the recommended design won.
 *
 * <p>Each contribution carries the raw measurement, the reference range it was normalised against,
 * the weight and the product. All four are needed to check the arithmetic; a normalised value on
 * its own cannot be argued with.
 *
 * <p>Generation penalties are listed separately from metric contributions on purpose. They shape
 * the routes the engine proposes rather than scoring the ones it has, so adding them into a total
 * score would double-count a preference that already changed the geometry. WP6A-2 renders them
 * under their own heading for the same reason.
 */
@JsonIgnoreProperties(ignoreUnknown = true)
public record PythonScoringExplanation(
        @JsonProperty("profile_id") String profileId,
        @JsonProperty("reference_ranges_version") String referenceRangesVersion,
        @JsonProperty("candidates") List<CandidateExplanation> candidates,
        @JsonProperty("generation_penalties") List<GenerationPenalty> generationPenalties
) {

    @JsonIgnoreProperties(ignoreUnknown = true)
    public record CandidateExplanation(
            @JsonProperty("candidate_id") String candidateId,
            @JsonProperty("eligible") Boolean eligible,
            /** Null for a candidate that was not ranked, which is not the same as ranked last. */
            @JsonProperty("rank") Integer rank,
            @JsonProperty("total_score") Double totalScore,
            @JsonProperty("contributions") List<MetricContribution> contributions
    ) {
    }

    @JsonIgnoreProperties(ignoreUnknown = true)
    public record MetricContribution(
            @JsonProperty("metric") String metric,
            /** {@code minimise} or {@code maximise}: which direction is better for this metric. */
            @JsonProperty("direction") String direction,
            @JsonProperty("raw_value") Double rawValue,
            @JsonProperty("reference_min") Double referenceMin,
            @JsonProperty("reference_max") Double referenceMax,
            @JsonProperty("normalised_value") Double normalisedValue,
            @JsonProperty("weight") Double weight,
            @JsonProperty("weighted_contribution") Double weightedContribution
    ) {
    }

    @JsonIgnoreProperties(ignoreUnknown = true)
    public record GenerationPenalty(
            @JsonProperty("name") String name,
            @JsonProperty("value") Double value,
            @JsonProperty("unit") String unit
    ) {
    }
}
