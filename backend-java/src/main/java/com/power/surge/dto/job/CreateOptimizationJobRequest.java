package com.power.surge.dto.job;

import java.math.BigDecimal;

/**
 * What the browser may ask for when it starts a run.
 *
 * <p>{@code profileId} is a C6 profile ID and nothing else. A client cannot send a version, a
 * weight, a reference range or a whole definition: Java pins the version from its allow-list and
 * Python owns the values. That keeps one policy in force per deployment — a caller cannot assemble
 * a private scoring policy by hand and have a result come back looking like a sanctioned one.
 *
 * <p>Null means a V0 run, per C1.
 */
public record CreateOptimizationJobRequest(
        String algorithmType,
        String scenario,
        BigDecimal capexWeight,
        BigDecimal lossesWeight,
        BigDecimal maxSpanMeters,
        BigDecimal voltageKv,
        BigDecimal feederCapacityMw,
        BigDecimal maxVoltageDropPct,
        BigDecimal rowWidthM,
        String profileId
) {

    /** A V0 request: everything the API took before profiles existed, and no profile. */
    public CreateOptimizationJobRequest(
            String algorithmType,
            String scenario,
            BigDecimal capexWeight,
            BigDecimal lossesWeight,
            BigDecimal maxSpanMeters,
            BigDecimal voltageKv,
            BigDecimal feederCapacityMw,
            BigDecimal maxVoltageDropPct,
            BigDecimal rowWidthM
    ) {
        this(algorithmType, scenario, capexWeight, lossesWeight, maxSpanMeters, voltageKv,
                feederCapacityMw, maxVoltageDropPct, rowWidthM, null);
    }
}
