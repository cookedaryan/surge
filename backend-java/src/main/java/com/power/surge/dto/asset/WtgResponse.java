package com.power.surge.dto.asset;

import java.math.BigDecimal;
import java.time.Instant;
import java.util.UUID;

public record WtgResponse(
        UUID id,
        String externalId,
        BigDecimal capacityMw,
        double longitude,
        double latitude,
        Instant createdAt
) {
}
