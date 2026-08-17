package com.power.surge.dto.client.python;

import com.fasterxml.jackson.annotation.JsonProperty;

import java.util.Map;

public record PythonOptimisationRequest(
        @JsonProperty("request_id") String requestId,
        @JsonProperty("project_id") String projectId,
        @JsonProperty("scenario") String scenario,
        @JsonProperty("wtg_geojson") Map<String, Object> wtgGeojson,
        @JsonProperty("substation_geojson") Map<String, Object> substationGeojson,
        @JsonProperty("electrical_params") Map<String, Object> electricalParams,
        @JsonProperty("pole_config") Map<String, Object> poleConfig,
        @JsonProperty("avoidance_geojson") Map<String, Object> avoidanceGeojson,
        @JsonProperty("scoring_weights") Map<String, Object> scoringWeights,
        /**
         * The conductors the optimiser may size against.
         *
         * <p>Omitted, the engine synthesises a single fictional cable from the feeder-capacity
         * input and every electrical result rests on placeholder impedances. Supplied, per-segment
         * sizing has a real range to choose from.
         */
        @JsonProperty("cable_config") Map<String, Object> cableConfig
) {
}
