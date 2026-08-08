package com.power.surge.dto.route;

import com.power.surge.domain.GeneratedRoute;
import org.locationtech.jts.geom.Coordinate;

import java.math.BigDecimal;
import java.time.Instant;
import java.util.ArrayList;
import java.util.List;
import java.util.UUID;

public record GeneratedRouteResponse(
        UUID id,
        UUID jobId,
        String feederName,
        BigDecimal totalLengthMeters,
        BigDecimal totalCost,
        BigDecimal electricalLossesKw,
        Integer poleCount,
        List<List<Double>> routeCoordinates,
        List<List<Double>> poleCoordinates,
        Instant createdAt
) {
    public static GeneratedRouteResponse fromEntity(GeneratedRoute route) {
        List<List<Double>> coords = new ArrayList<>();
        if (route.getRoutePath() != null) {
            for (Coordinate c : route.getRoutePath().getCoordinates()) {
                coords.add(List.of(c.getX(), c.getY()));
            }
        }

        List<List<Double>> poleCoords = new ArrayList<>();
        if (route.getPoleLocations() != null) {
            for (Coordinate c : route.getPoleLocations().getCoordinates()) {
                poleCoords.add(List.of(c.getX(), c.getY()));
            }
        }

        return new GeneratedRouteResponse(
                route.getId(),
                route.getJob().getId(),
                route.getFeederName(),
                route.getTotalLengthMeters(),
                route.getTotalCost(),
                route.getElectricalLossesKw(),
                route.getPoleCount(),
                coords,
                poleCoords.isEmpty() ? null : poleCoords,
                route.getCreatedAt()
        );
    }
}
