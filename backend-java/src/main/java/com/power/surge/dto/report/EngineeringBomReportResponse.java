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
        /**
         * The network's CAPEX as the engine priced it, or null when the run was not costed.
         *
         * <p>Null rather than zero, and a consumer must render it as "not costed" rather than as a
         * number: a run without a cost catalogue is one whose price is unknown, not one that is free.
         * This was previously the sum of a per-route {@code length × 80} fabrication.
         */
        BigDecimal totalEstimatedCost,
        /** ISO 4217 code for every money figure here, or null when the run was not costed. */
        String costCurrency,
        /**
         * Components the engine could not price, or null when the run was not costed.
         *
         * <p>Above zero, {@code totalEstimatedCost} is a partial sum: the engine leaves a component
         * out rather than pricing a gap at zero.
         */
        Integer costFailureCount,
        BigDecimal conductorCapex,
        BigDecimal poleCapex,
        BigDecimal landCapex,
        BigDecimal annualLossEnergyMwh,
        BigDecimal annualLossCost,
        BigDecimal presentValueOpex,
        BigDecimal lifecycleCost,
        BigDecimal totalElectricalLossesKw,
        BigDecimal rowWidthMeters,
        BigDecimal totalAffectedAreaM2,
        BigDecimal totalCompensationCost,
        List<FeederBomSummary> feederSummaries,
        List<RouteSegmentDetail> segmentDetails,
        List<PoleScheduleEntry> poleSchedule,
        Integer ownerInteractionCount,
        String ownerInteractionBasis,
        String landCostBasis,
        Boolean landIsFeasible,
        List<ParcelImpactSummary> parcelImpactSummaries,
        Instant generatedAt
) {
}
