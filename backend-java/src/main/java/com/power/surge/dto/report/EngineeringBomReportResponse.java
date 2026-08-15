package com.power.surge.dto.report;

import java.math.BigDecimal;
import java.time.Instant;
import java.util.List;
import java.util.Map;
import java.util.UUID;

/**
 * The full engineering bill of materials for one optimisation run.
 *
 * <p>Carries the run's inputs, a feeder-level roll-up, the per-segment schedule with coordinates,
 * every pole with its type and position, and the land impact — enough to price the network, build
 * it, and check the figures without going back to the application.
 *
 * <p>{@code totalFeeders} counts distinct feeders. It previously counted route rows, so the
 * reference project reported 38 feeders where it has seven.
 */
public record EngineeringBomReportResponse(
        UUID projectId,
        String projectName,
        UUID jobId,
        ReportRunParameters runParameters,
        Integer totalFeeders,
        Integer totalSegments,
        BigDecimal totalNetworkLengthMeters,
        Integer totalPoles,
        Map<String, Integer> poleCountByRole,
        Map<String, Integer> poleCountByType,
        BigDecimal totalEstimatedCost,
        BigDecimal totalElectricalLossesKw,
        BigDecimal rowWidthMeters,
        BigDecimal totalAffectedAreaM2,
        BigDecimal totalCompensationCost,
        List<FeederBomSummary> feederSummaries,
        List<RouteSegmentDetail> segmentDetails,
        List<PoleScheduleEntry> poleSchedule,
        List<ParcelImpactSummary> parcelImpactSummaries,
        Instant generatedAt
) {
}
