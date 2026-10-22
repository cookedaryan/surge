package com.power.surge.dto.client.python;

import com.fasterxml.jackson.annotation.JsonIgnoreProperties;
import com.fasterxml.jackson.annotation.JsonProperty;

/**
 * Contract C2 {@code solver_runs}: one MILP solve, its outcome and what bounded it.
 *
 * <p>{@code status} is read as a String, not an enum. C2 is an additive contract and the status
 * vocabulary can gain a value; binding to a Java enum would turn that addition into a parse failure
 * that reads like a broken engine. The conformance test checks instead that every status the schema
 * lists survives a round trip, which is the property that actually matters.
 *
 * <p>A {@code LIMIT_REACHED} solve is a result, not a failure: it means the solver stopped at its
 * time or node budget with the best answer it had. Treating it as infeasible is the mistake WP4-6
 * exists to prevent, and {@code limitReached} is what tells them apart.
 */
@JsonIgnoreProperties(ignoreUnknown = true)
public record PythonSolverRun(
        @JsonProperty("objective") String objective,
        @JsonProperty("status") String status,
        @JsonProperty("feeder_count") Integer feederCount,
        @JsonProperty("wall_time_s") Double wallTimeS,
        @JsonProperty("mip_gap") Double mipGap,
        @JsonProperty("limit_reached") Boolean limitReached,
        /** Null when no budget was applied, which is not the same as a budget of zero. */
        @JsonProperty("time_limit_s") Double timeLimitS,
        @JsonProperty("node_limit") Integer nodeLimit
) {
}
