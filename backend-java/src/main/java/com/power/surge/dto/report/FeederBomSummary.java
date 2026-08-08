package com.power.surge.dto.report;

import java.math.BigDecimal;

public record FeederBomSummary(
        String feederName,
        BigDecimal lengthMeters,
        Integer poleCount,
        BigDecimal totalCost,
        BigDecimal electricalLossesKw
) {
}
