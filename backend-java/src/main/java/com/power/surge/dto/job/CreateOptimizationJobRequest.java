package com.power.surge.dto.job;

import java.math.BigDecimal;

public record CreateOptimizationJobRequest(
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
}
