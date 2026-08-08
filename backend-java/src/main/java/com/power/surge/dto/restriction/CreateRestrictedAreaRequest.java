package com.power.surge.dto.restriction;

import java.math.BigDecimal;
import java.util.List;

public record CreateRestrictedAreaRequest(
        String name,
        String restrictionType,
        BigDecimal bufferMeters,
        List<List<List<Double>>> coordinates
) {
}
