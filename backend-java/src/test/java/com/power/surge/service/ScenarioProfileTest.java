package com.power.surge.service;

import org.junit.jupiter.api.Test;
import org.junit.jupiter.params.ParameterizedTest;
import org.junit.jupiter.params.provider.ValueSource;

import java.util.List;
import java.util.Map;
import java.util.Set;
import java.util.stream.Collectors;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.within;

/**
 * The four MVP scenarios must be genuinely different optimisation configurations, not four labels
 * on one configuration. These tests are the regression guard against the scenario selector
 * silently decaying back into a no-op.
 */
class ScenarioProfileTest {

    private static final List<String> ALL_SCENARIOS = List.of(
            ScenarioProfile.BALANCED,
            ScenarioProfile.MINIMUM_COST,
            ScenarioProfile.MINIMUM_LAND_IMPACT,
            ScenarioProfile.MINIMUM_ENVIRONMENTAL_IMPACT
    );

    /**
     * The Python contract rejects any weight vector that does not total 1.0
     * ({@code ScoringWeightsRequest.validate_weight_total}), so a bad profile here would fail every
     * job for that scenario at runtime rather than at build time.
     */
    @ParameterizedTest
    @ValueSource(strings = {
            ScenarioProfile.BALANCED,
            ScenarioProfile.MINIMUM_COST,
            ScenarioProfile.MINIMUM_LAND_IMPACT,
            ScenarioProfile.MINIMUM_ENVIRONMENTAL_IMPACT
    })
    void everyScenarioProducesWeightsThatSumToOne(String scenario) {
        ScenarioProfile profile = ScenarioProfile.forScenario(scenario);

        double total = profile.routeLengthWeight()
                + profile.electricalLossWeight()
                + profile.cableLoadingWeight()
                + profile.voltageMarginWeight();

        assertThat(total).isCloseTo(1.0, within(1e-9));
    }

    /** Python validates each individual weight as 0.0 <= w <= 1.0. */
    @ParameterizedTest
    @ValueSource(strings = {
            ScenarioProfile.BALANCED,
            ScenarioProfile.MINIMUM_COST,
            ScenarioProfile.MINIMUM_LAND_IMPACT,
            ScenarioProfile.MINIMUM_ENVIRONMENTAL_IMPACT
    })
    void everyIndividualWeightIsWithinTheAcceptedRange(String scenario) {
        ScenarioProfile.forScenario(scenario).scoringWeights().values()
                .forEach(weight -> assertThat((Double) weight).isBetween(0.0, 1.0));
    }

    /**
     * The core guarantee: no two scenarios may resolve to the same optimisation configuration.
     * A configuration is the weight vector plus the constraint bias, because either one alone is
     * insufficient to differentiate every project.
     */
    @Test
    void noTwoScenariosShareTheSameOptimisationConfiguration() {
        Set<String> configurations = ALL_SCENARIOS.stream()
                .map(ScenarioProfile::forScenario)
                .map(p -> p.scoringWeights() + "|"
                        + p.crossingCostMultiplier() + "|"
                        + p.parcelCostMultiplier() + "|"
                        + p.watercourseCostMultiplier() + "|"
                        + p.restrictedBufferBonusM())
                .collect(Collectors.toSet());

        assertThat(configurations).hasSameSizeAs(ALL_SCENARIOS);
    }

    /**
     * Scoring weights cannot differentiate a project in which only one candidate survives
     * electrical screening, which is the common case on real survey data. Every scenario therefore
     * has to bias the cost surface too, so the generated routes differ before scoring runs.
     */
    @Test
    void everyNonBaselineScenarioAlsoBiasesTheCostSurface() {
        ScenarioProfile balanced = ScenarioProfile.forScenario(ScenarioProfile.BALANCED);

        for (String scenario : ALL_SCENARIOS) {
            if (ScenarioProfile.BALANCED.equals(scenario)) {
                continue;
            }
            ScenarioProfile profile = ScenarioProfile.forScenario(scenario);
            boolean biasesSurface =
                    profile.crossingCostMultiplier() != balanced.crossingCostMultiplier()
                            || profile.parcelCostMultiplier() != balanced.parcelCostMultiplier()
                            || profile.watercourseCostMultiplier() != balanced.watercourseCostMultiplier()
                            || profile.restrictedBufferBonusM() != balanced.restrictedBufferBonusM();

            assertThat(biasesSurface)
                    .as("%s must change the cost surface, not only the scoring weights", scenario)
                    .isTrue();
        }
    }

    @Test
    void balancedLeavesImportedConstraintsExactlyAsTheyWereCaptured() {
        ScenarioProfile balanced = ScenarioProfile.forScenario(ScenarioProfile.BALANCED);

        assertThat(balanced.crossingCost(42.0)).isEqualTo(42.0);
        assertThat(balanced.parcelCost()).isEqualTo(ScenarioProfile.DEFAULT_SOFT_COST_WEIGHT);
        assertThat(balanced.restrictedBufferMeters(30.0)).isEqualTo(30.0);
        // No stored buffer resolves to Python's own default, so behaviour is unchanged.
        assertThat(balanced.restrictedBufferMeters(null))
                .isEqualTo(ScenarioProfile.DEFAULT_AVOIDANCE_BUFFER_M);
    }

    @Test
    void minimumCostIsMoreWillingToCrossSoftConstraintsToShortenTheNetwork() {
        ScenarioProfile balanced = ScenarioProfile.forScenario(ScenarioProfile.BALANCED);
        ScenarioProfile minimumCost = ScenarioProfile.forScenario(ScenarioProfile.MINIMUM_COST);

        assertThat(minimumCost.parcelCost()).isLessThan(balanced.parcelCost());
        assertThat(minimumCost.crossingCost(null)).isLessThan(balanced.crossingCost(null));
        assertThat(minimumCost.routeLengthWeight()).isGreaterThan(balanced.routeLengthWeight());
    }

    @Test
    void minimumLandImpactMakesParcelTraversalExpensiveWithoutPenalisingRoads() {
        ScenarioProfile balanced = ScenarioProfile.forScenario(ScenarioProfile.BALANCED);
        ScenarioProfile minimumLand = ScenarioProfile.forScenario(ScenarioProfile.MINIMUM_LAND_IMPACT);

        assertThat(minimumLand.parcelCost()).isGreaterThan(balanced.parcelCost());
        assertThat(minimumLand.crossingCost(null)).isEqualTo(balanced.crossingCost(null));
    }

    /**
     * A hard exclusion must not carry {@code cost_weight} — Python raises on that — so the
     * environmental preference is expressed as additional routing clearance instead.
     */
    @Test
    void minimumEnvironmentalImpactWidensClearanceAndPenalisesWatercourses() {
        ScenarioProfile balanced = ScenarioProfile.forScenario(ScenarioProfile.BALANCED);
        ScenarioProfile minimumEnv =
                ScenarioProfile.forScenario(ScenarioProfile.MINIMUM_ENVIRONMENTAL_IMPACT);

        assertThat(minimumEnv.restrictedBufferMeters(30.0))
                .isGreaterThan(balanced.restrictedBufferMeters(30.0));
        assertThat(minimumEnv.restrictedBufferMeters(null))
                .isGreaterThan(balanced.restrictedBufferMeters(null));
        assertThat(minimumEnv.watercourseCost(null)).isGreaterThan(balanced.watercourseCost(null));
    }

    @Test
    void scoringWeightsUseTheKeysThePythonContractExpects() {
        Map<String, Object> weights =
                ScenarioProfile.forScenario(ScenarioProfile.BALANCED).scoringWeights();

        assertThat(weights).containsOnlyKeys(
                "route_length_weight",
                "electrical_loss_weight",
                "cable_loading_weight",
                "voltage_margin_weight");
    }

    @Test
    void unknownBlankAndNullScenariosFallBackToBalancedRatherThanFailingTheJob() {
        ScenarioProfile balanced = ScenarioProfile.forScenario(ScenarioProfile.BALANCED);

        assertThat(ScenarioProfile.forScenario(null)).isEqualTo(balanced);
        assertThat(ScenarioProfile.forScenario("")).isEqualTo(balanced);
        assertThat(ScenarioProfile.forScenario("Not A Real Scenario")).isEqualTo(balanced);
    }

    @Test
    void scenarioLookupToleratesCasingAndSurroundingWhitespace() {
        ScenarioProfile expected = ScenarioProfile.forScenario(ScenarioProfile.MINIMUM_LAND_IMPACT);

        assertThat(ScenarioProfile.forScenario("  minimum land impact  ")).isEqualTo(expected);
        assertThat(ScenarioProfile.forScenario("MINIMUM LAND IMPACT")).isEqualTo(expected);
    }
}
