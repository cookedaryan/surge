package com.power.surge.dto.report;

import java.math.BigDecimal;

/**
 * One feeder, aggregated across every segment that makes it up.
 *
 * <p>This used to be produced one-per-route-row, so a feeder spanning six segments appeared six
 * times over and the "feeder count" was really a segment count. Per-segment figures now live in
 * {@link RouteSegmentDetail}; this is the feeder-level roll-up.
 */
public record FeederBomSummary(
        String feederName,
        Integer segmentCount,
        BigDecimal lengthMeters,
        Integer poleCount,
        BigDecimal totalCost,
        BigDecimal electricalLossesKw
) {
}
