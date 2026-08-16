package com.power.surge.dto.report;

import java.math.BigDecimal;

/**
 * One physical run of line between two points on the network.
 *
 * <p>A feeder is built from several of these — the reference project's seven feeders span 38
 * segments — so this is the level a crew actually builds from, and the level the map draws.
 * Endpoint coordinates are carried so a segment can be located on the ground without opening the
 * map, and the full path as WKT so nothing about the geometry is lost in export.
 */
public record RouteSegmentDetail(
        String feederName,
        String segmentId,
        BigDecimal lengthMeters,
        Integer poleCount,
        BigDecimal totalCost,
        BigDecimal electricalLossesKw,
        Double startLatitude,
        Double startLongitude,
        Double endLatitude,
        Double endLongitude,
        Integer vertexCount,
        String pathWkt
) {
}
