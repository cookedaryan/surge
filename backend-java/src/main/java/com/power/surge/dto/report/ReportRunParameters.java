package com.power.surge.dto.report;

import java.math.BigDecimal;
import java.time.Instant;

/**
 * The inputs the reported network was produced from.
 *
 * <p>Without these a bill of materials cannot be checked or reproduced: the same site yields a
 * different network at a different voltage, feeder capacity or span limit, and the four scenarios
 * change the constraint costs the optimiser solves against. Anyone reviewing the numbers needs to
 * know which run they belong to.
 */
public record ReportRunParameters(
        String scenario,
        String algorithmType,
        String status,
        BigDecimal voltageKv,
        BigDecimal feederCapacityMw,
        BigDecimal maxSpanMeters,
        BigDecimal maxVoltageDropPct,
        BigDecimal rowWidthMeters,
        BigDecimal capexWeight,
        BigDecimal lossesWeight,
        Instant startedAt,
        Instant completedAt
) {
}
