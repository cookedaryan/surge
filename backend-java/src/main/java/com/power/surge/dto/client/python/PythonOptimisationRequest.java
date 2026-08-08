package com.power.surge.dto.client.python;

import com.fasterxml.jackson.annotation.JsonProperty;

import java.util.Map;

public record PythonOptimisationRequest(
        @JsonProperty("request_id") String requestId,
        @JsonProperty("project_id") String projectId,
        @JsonProperty("scenario") String scenario,
        @JsonProperty("wtg_geojson") Map<String, Object> wtgGeojson,
        @JsonProperty("substation_geojson") Map<String, Object> substationGeojson,
        @JsonProperty("electrical_params") Map<String, Object> electricalParams
) {
}
