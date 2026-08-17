package com.power.surge.service;

import com.power.surge.dto.client.python.PythonOptimisationResponse;

import java.math.BigDecimal;
import java.math.RoundingMode;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;

/**
 * The conductor the optimiser selected for one segment.
 *
 * @param cableTypeId        catalogue id of the chosen conductor
 * @param requiredCurrentA   current the segment has to carry
 * @param effectiveAmpacityA what the chosen conductor can carry, after derating and parallel runs
 * @param utilisationPct     the first as a percentage of the second
 */
public record CableSelection(
        String cableTypeId,
        BigDecimal requiredCurrentA,
        BigDecimal effectiveAmpacityA,
        BigDecimal utilisationPct
) {

    /**
     * Reads the recommended candidate's per-segment conductor selection out of an engine response.
     *
     * <p>The engine has sized cables per segment since PY-030 and reported them on every candidate,
     * but nothing here read them, so the bill of materials could not name the conductor it was
     * pricing.
     *
     * <p>Only the recommended candidate's sizing is taken. The others describe networks that were
     * not chosen, and attributing their conductors to the segments actually being built would be
     * wrong in a way that looks perfectly plausible in a report.
     *
     * <p>Returns an empty map rather than throwing when anything is missing or malformed. A run
     * that produced no sizing must still persist its routes — losing a whole network because one
     * optional field was absent would be a poor trade.
     */
    public static Map<String, CableSelection> fromResponse(PythonOptimisationResponse response) {
        Map<String, CableSelection> bySegment = new LinkedHashMap<>();
        if (response == null || response.candidates() == null || response.candidates().isEmpty()) {
            return bySegment;
        }

        Map<String, Object> candidate = recommendedCandidate(response);
        if (candidate == null) {
            return bySegment;
        }
        Object sizing = candidate.get("cable_sizing");
        if (!(sizing instanceof Map<?, ?> sizingMap)) {
            return bySegment;
        }
        Object assignments = sizingMap.get("assignments");
        if (!(assignments instanceof List<?> assignmentList)) {
            return bySegment;
        }

        for (Object entry : assignmentList) {
            if (!(entry instanceof Map<?, ?> assignment)) {
                continue;
            }
            String segmentId = text(assignment.get("segment_id"));
            String cableTypeId = text(assignment.get("selected_cable_type_id"));
            if (segmentId == null || cableTypeId == null) {
                continue;
            }
            BigDecimal required = decimal(assignment.get("required_current_a"), 2);
            BigDecimal ampacity = decimal(assignment.get("effective_ampacity_a"), 2);
            BigDecimal fraction = decimal(assignment.get("utilization_fraction"), 6);
            BigDecimal utilisation = fraction != null
                    ? fraction.multiply(BigDecimal.valueOf(100)).setScale(2, RoundingMode.HALF_UP)
                    : null;
            bySegment.put(segmentId, new CableSelection(cableTypeId, required, ampacity, utilisation));
        }
        return bySegment;
    }

    /**
     * The candidate the engine recommended, or null if it cannot be identified.
     *
     * <p>Falls back to nothing rather than to the first candidate: guessing here would silently
     * attribute a rejected network's conductors to the built one.
     */
    private static Map<String, Object> recommendedCandidate(PythonOptimisationResponse response) {
        String recommendedId = response.recommendation() != null
                ? text(response.recommendation().get("recommended_scenario_id"))
                : null;
        if (recommendedId == null) {
            return null;
        }
        for (Map<String, Object> candidate : response.candidates()) {
            if (candidate != null && recommendedId.equals(text(candidate.get("scenario_id")))) {
                return candidate;
            }
        }
        return null;
    }

    private static String text(Object value) {
        if (value == null) {
            return null;
        }
        String s = String.valueOf(value).trim();
        return s.isEmpty() ? null : s;
    }

    private static BigDecimal decimal(Object value, int scale) {
        if (!(value instanceof Number number)) {
            return null;
        }
        double d = number.doubleValue();
        if (Double.isNaN(d) || Double.isInfinite(d)) {
            return null;
        }
        return BigDecimal.valueOf(d).setScale(scale, RoundingMode.HALF_UP);
    }
}
