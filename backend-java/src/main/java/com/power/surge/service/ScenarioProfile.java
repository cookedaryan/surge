package com.power.surge.service;

import java.util.LinkedHashMap;
import java.util.Locale;
import java.util.Map;

/**
 * Deterministic optimisation profile for one of the four MVP scenarios.
 *
 * <p>Scenarios are differentiated by two independent mechanisms, and both are required:
 *
 * <ol>
 *   <li><b>Scoring weights</b> re-rank candidates that have already been generated and
 *       electrically screened (consumed by the Python {@code CandidateScoringConfig}).</li>
 *   <li><b>Constraint cost and clearance bias</b> reshapes the A* cost surface, so the candidate
 *       routes themselves differ before any scoring happens.</li>
 * </ol>
 *
 * <p>Scoring weights alone are not sufficient. When only one candidate survives electrical
 * screening — the common case on real survey data — that sole eligible candidate wins under
 * every possible weight vector, making mechanism 1 a no-op. Biasing the cost surface changes
 * the geometry that gets generated in the first place, so each scenario also carries constraint
 * multipliers.
 *
 * <p>The four weights must sum to exactly 1.0; the Python contract rejects any other total.
 */
public record ScenarioProfile(
        String scenario,
        double routeLengthWeight,
        double electricalLossWeight,
        double cableLoadingWeight,
        double voltageMarginWeight,
        double crossingCostMultiplier,
        double parcelCostMultiplier,
        double watercourseCostMultiplier,
        double restrictedBufferBonusM
) {

    /**
     * Python's fallback cost for a soft constraint feature that carries no explicit
     * {@code cost_weight} ({@code apply_avoidance_constraints}). Used as the multiplier base so a
     * multiplier of 1.0 reproduces today's behaviour exactly.
     */
    public static final double DEFAULT_SOFT_COST_WEIGHT = 20.0;

    /**
     * Python's default {@code avoidance_buffer_m} ({@code RoutingConfigRequest}). Used as the
     * clearance base when a restricted area has no stored buffer, so adding an environmental
     * bonus can never resolve to less clearance than the engine would have applied anyway.
     */
    public static final double DEFAULT_AVOIDANCE_BUFFER_M = 10.0;

    public static final String BALANCED = "Balanced";
    public static final String MINIMUM_COST = "Minimum Cost";
    public static final String MINIMUM_LAND_IMPACT = "Minimum Land Impact";
    public static final String MINIMUM_ENVIRONMENTAL_IMPACT = "Minimum Environmental Impact";

    /** Even weighting; constraints left exactly as imported. The reference scenario. */
    private static final ScenarioProfile BALANCED_PROFILE = new ScenarioProfile(
            BALANCED, 0.40, 0.25, 0.20, 0.15, 1.0, 1.0, 1.0, 0.0);

    /**
     * Route length dominates scoring (it is the current CAPEX proxy), and soft crossing penalties
     * are halved so the router will accept a road or parcel crossing that shortens the network.
     */
    private static final ScenarioProfile MINIMUM_COST_PROFILE = new ScenarioProfile(
            MINIMUM_COST, 0.70, 0.12, 0.10, 0.08, 0.5, 0.5, 0.5, 0.0);

    /** Parcel traversal is made expensive so the router prefers routes over less private land. */
    private static final ScenarioProfile MINIMUM_LAND_IMPACT_PROFILE = new ScenarioProfile(
            MINIMUM_LAND_IMPACT, 0.40, 0.25, 0.20, 0.15, 1.0, 3.0, 1.0, 0.0);

    /**
     * Watercourse crossings are made expensive and every restricted/environmental zone gains an
     * extra 25 m of routing clearance on top of its imported buffer.
     */
    private static final ScenarioProfile MINIMUM_ENVIRONMENTAL_IMPACT_PROFILE = new ScenarioProfile(
            MINIMUM_ENVIRONMENTAL_IMPACT, 0.40, 0.25, 0.20, 0.15, 1.0, 1.0, 3.0, 25.0);

    /**
     * Resolves a scenario label to its profile. Unknown, blank and {@code null} labels fall back
     * to {@link #BALANCED} rather than failing a job over a display string.
     */
    public static ScenarioProfile forScenario(String scenario) {
        if (scenario == null) {
            return BALANCED_PROFILE;
        }
        return switch (scenario.trim().toLowerCase(Locale.ROOT)) {
            case "minimum cost" -> MINIMUM_COST_PROFILE;
            case "minimum land impact" -> MINIMUM_LAND_IMPACT_PROFILE;
            case "minimum environmental impact" -> MINIMUM_ENVIRONMENTAL_IMPACT_PROFILE;
            default -> BALANCED_PROFILE;
        };
    }

    /** The weights in the shape the Python {@code scoring_weights} contract expects. */
    public Map<String, Object> scoringWeights() {
        Map<String, Object> weights = new LinkedHashMap<>();
        weights.put("route_length_weight", routeLengthWeight);
        weights.put("electrical_loss_weight", electricalLossWeight);
        weights.put("cable_loading_weight", cableLoadingWeight);
        weights.put("voltage_margin_weight", voltageMarginWeight);
        return weights;
    }

    /**
     * Effective soft cost for a road or HT line, scaling the imported crossing cost when one was
     * captured and Python's documented default otherwise.
     */
    public double crossingCost(Double importedCrossingCost) {
        double base = importedCrossingCost != null ? importedCrossingCost : DEFAULT_SOFT_COST_WEIGHT;
        return base * crossingCostMultiplier;
    }

    /** Effective soft cost for a watercourse, which the environmental scenario weights separately. */
    public double watercourseCost(Double importedCrossingCost) {
        double base = importedCrossingCost != null ? importedCrossingCost : DEFAULT_SOFT_COST_WEIGHT;
        return base * watercourseCostMultiplier;
    }

    /** Effective soft cost for a cadastral parcel. */
    public double parcelCost() {
        return DEFAULT_SOFT_COST_WEIGHT * parcelCostMultiplier;
    }

    /** Effective hard-exclusion clearance for a restricted area, including any scenario bonus. */
    public double restrictedBufferMeters(Double importedBufferMeters) {
        double base = importedBufferMeters != null ? importedBufferMeters : DEFAULT_AVOIDANCE_BUFFER_M;
        return base + restrictedBufferBonusM;
    }
}
