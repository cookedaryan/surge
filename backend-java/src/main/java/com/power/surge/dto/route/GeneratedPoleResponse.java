package com.power.surge.dto.route;

import com.power.surge.domain.GeneratedPole;

import java.time.Instant;
import java.util.List;
import java.util.UUID;

public record GeneratedPoleResponse(
        UUID id,
        UUID jobId,
        String poleIdentifier,
        String feederName,
        String poleRole,
        String recommendedPoleType,
        List<String> connectedFeederIds,
        List<Double> location,
        Instant createdAt
) {
    public static GeneratedPoleResponse fromEntity(GeneratedPole pole) {
        List<Double> coords = pole.getLocation() != null
                ? List.of(pole.getLocation().getX(), pole.getLocation().getY())
                : null;

        return new GeneratedPoleResponse(
                pole.getId(),
                pole.getJob().getId(),
                pole.getPoleIdentifier(),
                pole.getFeederName(),
                pole.getPoleRole(),
                pole.getRecommendedPoleType(),
                pole.getConnectedFeederIds(),
                coords,
                pole.getCreatedAt()
        );
    }
}
