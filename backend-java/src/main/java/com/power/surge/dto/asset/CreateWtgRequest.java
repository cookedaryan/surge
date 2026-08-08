package com.power.surge.dto.asset;

import jakarta.validation.constraints.DecimalMax;
import jakarta.validation.constraints.DecimalMin;
import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.NotNull;
import jakarta.validation.constraints.Positive;
import jakarta.validation.constraints.Size;

import java.math.BigDecimal;

public record CreateWtgRequest(
        @NotBlank(message = "External ID is required.")
        @Size(max = 100, message = "External ID must not exceed 100 characters.")
        String externalId,

        @NotNull(message = "Capacity is required.")
        @Positive(message = "Capacity must be greater than zero.")
        BigDecimal capacityMw,

        @NotNull(message = "Longitude is required.")
        @DecimalMin(value = "-180.0", message = "Longitude must be >= -180.")
        @DecimalMax(value = "180.0", message = "Longitude must be <= 180.")
        Double longitude,

        @NotNull(message = "Latitude is required.")
        @DecimalMin(value = "-90.0", message = "Latitude must be >= -90.")
        @DecimalMax(value = "90.0", message = "Latitude must be <= 90.")
        Double latitude
) {
}
