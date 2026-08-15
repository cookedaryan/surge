package com.power.surge.dto.report;

/**
 * One pole, as it would appear on a setting-out schedule.
 *
 * <p>Coordinates are what makes this usable in the field, so they are given to six decimal places
 * — roughly 0.11 m at this latitude, finer than a pole can be positioned. {@code role} is what the
 * pole does structurally (tangent, angle, junction, terminal) and drives the map layer it lands on;
 * {@code recommendedPoleType} is the actual product the optimiser selected for that duty.
 */
public record PoleScheduleEntry(
        String poleIdentifier,
        String feederName,
        String role,
        String recommendedPoleType,
        Double latitude,
        Double longitude,
        String connectedSegments
) {
}
