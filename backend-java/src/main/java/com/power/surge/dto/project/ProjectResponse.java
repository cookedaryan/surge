package com.power.surge.dto.project;

import java.time.Instant;
import java.util.UUID;

public record ProjectResponse(
        UUID id,
        String name,
        String description,
        String crs,
        Instant createdAt,
        Instant updatedAt
) {
}
