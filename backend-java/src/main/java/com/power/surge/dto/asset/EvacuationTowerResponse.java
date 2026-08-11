package com.power.surge.dto.asset;

import java.math.BigDecimal;
import java.time.Instant;
import java.util.UUID;

public record EvacuationTowerResponse(
        UUID id,
        String externalId,
        String towerType,
        BigDecimal heightM,
        String lineSection,
        String sourceFolder,
        double longitude,
        double latitude,
        Instant createdAt
) {
}
