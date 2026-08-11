package com.power.surge.dto.asset;

import com.power.surge.domain.LineType;

import java.math.BigDecimal;
import java.time.Instant;
import java.util.List;
import java.util.UUID;

/**
 * @param crossingConstraint whether a routed corridor crossing this feature should be penalised
 * @param coordinates        WGS84 [longitude, latitude] vertex pairs
 */
public record ReferenceLineResponse(
        UUID id,
        String externalId,
        LineType lineType,
        boolean crossingConstraint,
        BigDecimal voltageKv,
        BigDecimal lengthM,
        String sourceFolder,
        List<List<Double>> coordinates,
        Instant createdAt
) {
}
