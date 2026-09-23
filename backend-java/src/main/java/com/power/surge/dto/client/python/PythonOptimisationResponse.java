package com.power.surge.dto.client.python;

import com.fasterxml.jackson.annotation.JsonProperty;

import java.util.List;
import java.util.Map;

public record PythonOptimisationResponse(
        @JsonProperty("request_id") String requestId,
        @JsonProperty("status") String status,
        @JsonProperty("scenario") String scenario,
        @JsonProperty("feeder_routes_geojson") Map<String, Object> feederRoutesGeojson,
        @JsonProperty("poles_geojson") Map<String, Object> polesGeojson,
        @JsonProperty("metrics") Map<String, Object> metrics,
        @JsonProperty("workflow_status") String workflowStatus,
        @JsonProperty("candidates") List<Map<String, Object>> candidates,
        @JsonProperty("recommendation") Map<String, Object> recommendation,
        @JsonProperty("recommended_result") Map<String, Object> recommendedResult,
        @JsonProperty("failures") List<Map<String, Object>> failures,
        /**
         * C2 {@code effective_profile}, or {@code null} for a V0 response.
         *
         * <p>A C2 block is absent when it was not produced, so null here is the normal answer with
         * both flags off, not a missing field.
         */
        @JsonProperty("effective_profile") PythonEffectiveProfile effectiveProfile
) {

    /** A V0 response: everything the engine returned before the additive blocks existed. */
    public PythonOptimisationResponse(
            String requestId,
            String status,
            String scenario,
            Map<String, Object> feederRoutesGeojson,
            Map<String, Object> polesGeojson,
            Map<String, Object> metrics,
            String workflowStatus,
            List<Map<String, Object>> candidates,
            Map<String, Object> recommendation,
            Map<String, Object> recommendedResult,
            List<Map<String, Object>> failures
    ) {
        this(requestId, status, scenario, feederRoutesGeojson, polesGeojson, metrics,
                workflowStatus, candidates, recommendation, recommendedResult, failures, null);
    }
}
