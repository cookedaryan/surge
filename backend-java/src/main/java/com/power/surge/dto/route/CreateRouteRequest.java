package com.power.surge.dto.route;

import java.math.BigDecimal;
import java.util.List;

public record CreateRouteRequest(
        String feederName,
        BigDecimal totalLengthMeters,
        BigDecimal totalCost,
        BigDecimal electricalLossesKw,
        Integer poleCount,
        List<List<Double>> coordinates,
        List<List<Double>> poleCoordinates
) {
}
