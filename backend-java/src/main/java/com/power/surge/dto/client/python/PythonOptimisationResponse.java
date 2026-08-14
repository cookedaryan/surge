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
        @JsonProperty("failures") List<Map<String, Object>> failures
) {
}
