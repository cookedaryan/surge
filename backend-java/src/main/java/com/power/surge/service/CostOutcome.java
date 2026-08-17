package com.power.surge.service;

import com.power.surge.dto.client.python.PythonOptimisationResponse;

import java.math.BigDecimal;
import java.math.RoundingMode;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;

/**
 * The money the engine computed for the network that was chosen.
 *
 * <p>Since the optimiser was given rates it returns a full breakdown on every candidate: conductor
 * CAPEX per segment, pole CAPEX per class, land cost, losses valued over the analysis period, and a
 * lifecycle total. Nothing here read it, so every cost the product displayed came from
 * {@code route length × 80} — a constant with no basis, no currency and no provenance.
 *
 * <p>Every field is nullable on purpose. A run with no catalogue, or one whose catalogue missed a
 * conductor the run selected, genuinely has no cost, and a null says so where a zero would read as
 * free.
 *
 * @param conductorCostBySegment per-segment conductor cost — the only component the engine
 *                               attributes to an individual route
 * @param failureCount           components the engine could not price. Above zero the totals are
 *                               incomplete by construction, because the engine leaves a component
 *                               null rather than costing a gap at zero.
 */
public record CostOutcome(
        String currency,
        BigDecimal conductorCapex,
        BigDecimal poleCapex,
        BigDecimal landCapex,
        BigDecimal totalCapex,
        BigDecimal annualLossEnergyMwh,
        BigDecimal annualLossCost,
        BigDecimal presentValueOpex,
        BigDecimal lifecycleCost,
        String catalogueId,
        String catalogueVersion,
        String priceBasisDate,
        int failureCount,
        Map<String, BigDecimal> conductorCostBySegment
) {

    private static final CostOutcome UNCOSTED = new CostOutcome(
            null, null, null, null, null, null, null, null, null, null, null, null, 0, Map.of());

    /** What a run with no costing produces: absent figures, not zeroed ones. */
    public static CostOutcome uncosted() {
        return UNCOSTED;
    }

    /** True when the engine priced nothing, so callers can say "not costed" rather than print a 0. */
    public boolean isAbsent() {
        return totalCapex == null && lifecycleCost == null && conductorCostBySegment.isEmpty();
    }

    /**
     * Reads the recommended candidate's cost out of an engine response.
     *
     * <p>Only the recommended candidate's. The others price networks that were not chosen, and
     * attributing their money to the one being built would be wrong in a way that looks entirely
     * plausible in a report.
     *
     * <p>Returns {@link #uncosted()} rather than throwing when anything is missing. A run that
     * produced no cost must still persist its routes — losing a network because an optional field
     * was absent would be a poor trade.
     */
    public static CostOutcome fromResponse(PythonOptimisationResponse response) {
        Map<String, Object> candidate = recommendedCandidate(response);
        if (candidate == null) {
            return uncosted();
        }
        if (!(candidate.get("cost") instanceof Map<?, ?> cost)) {
            return uncosted();
        }

        return new CostOutcome(
                text(cost.get("currency")),
                decimal(cost.get("conductor_capex"), 2),
                decimal(cost.get("pole_capex"), 2),
                decimal(cost.get("land_capex"), 2),
                decimal(cost.get("total_capex"), 2),
                decimal(cost.get("annual_loss_energy_mwh"), 4),
                decimal(cost.get("annual_loss_cost"), 2),
                decimal(cost.get("present_value_opex"), 2),
                decimal(cost.get("lifecycle_cost"), 2),
                text(cost.get("catalogue_id")),
                text(cost.get("catalogue_version")),
                text(cost.get("catalogue_price_basis_date")),
                countFailures(cost.get("failures")),
                conductorCostBySegment(cost.get("line_items")));
    }

    /**
     * Conductor cost per segment, taken from the line items.
     *
     * <p>Only the {@code conductor} category is per-segment: pole costs are emitted per pole class
     * and land costs per parcel, so attributing either to one route would mean inventing an
     * apportionment the engine never made.
     */
    private static Map<String, BigDecimal> conductorCostBySegment(Object lineItems) {
        Map<String, BigDecimal> bySegment = new LinkedHashMap<>();
        if (!(lineItems instanceof List<?> items)) {
            return bySegment;
        }
        for (Object entry : items) {
            if (!(entry instanceof Map<?, ?> item)) {
                continue;
            }
            if (!"conductor".equals(text(item.get("category")))) {
                continue;
            }
            String segmentId = text(item.get("item_id"));
            BigDecimal amount = decimal(item.get("amount"), 2);
            if (segmentId == null || amount == null) {
                continue;
            }
            // A segment can appear more than once if the engine splits a run; summing is the only
            // reading that does not silently drop money.
            bySegment.merge(segmentId, amount, BigDecimal::add);
        }
        return bySegment;
    }

    private static int countFailures(Object failures) {
        return failures instanceof List<?> list ? list.size() : 0;
    }

    /**
     * The candidate the engine recommended, or null when it cannot be identified.
     *
     * <p>Falls back to nothing rather than to the first candidate: guessing would attribute a
     * rejected network's costs to the built one.
     */
    private static Map<String, Object> recommendedCandidate(PythonOptimisationResponse response) {
        if (response == null || response.candidates() == null || response.candidates().isEmpty()) {
            return null;
        }
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
