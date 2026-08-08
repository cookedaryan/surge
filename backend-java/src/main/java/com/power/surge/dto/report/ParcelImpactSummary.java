package com.power.surge.dto.report;

import java.math.BigDecimal;

public record ParcelImpactSummary(
        String parcelId,
        String ownerName,
        BigDecimal acquisitionCostPerM2,
        Double affectedAreaM2,
        BigDecimal estimatedCompensationCost
) {
}
