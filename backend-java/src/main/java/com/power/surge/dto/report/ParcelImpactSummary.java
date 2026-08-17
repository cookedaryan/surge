package com.power.surge.dto.report;

import java.math.BigDecimal;

public record ParcelImpactSummary(
        String parcelId,
        String ownerName,
        String ownerId,
        BigDecimal acquisitionCostPerM2,
        Double affectedAreaM2,
        BigDecimal estimatedCompensationCost,
        String availabilityStatus,
        String transactionMode,
        BigDecimal selectedPresentValue,
        String priceBasis,
        String priceDate
) {
}
