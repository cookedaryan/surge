package com.power.surge.dto.report;

import java.math.BigDecimal;
import java.time.Instant;
import java.util.List;
import java.util.UUID;

public record EngineeringBomReportResponse(
        UUID projectId,
        String projectName,
        UUID jobId,
        Integer totalFeeders,
        BigDecimal totalNetworkLengthMeters,
        Integer totalPoles,
        BigDecimal totalEstimatedCost,
        BigDecimal totalElectricalLossesKw,
        List<FeederBomSummary> feederSummaries,
        List<ParcelImpactSummary> parcelImpactSummaries,
        Instant generatedAt
) {
}
