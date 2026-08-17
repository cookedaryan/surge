package com.power.surge.service;

import com.power.surge.dto.client.python.PythonOptimisationResponse;
import org.junit.jupiter.api.Test;

import java.util.List;
import java.util.Map;

import static org.assertj.core.api.Assertions.assertThat;

/**
 * The optimiser has sized conductors per segment since PY-030 and reported them on every candidate.
 * Nothing here read them, so the bill of materials could not name the conductor it was pricing —
 * and conductor is the largest material cost in a collector network.
 */
class CableSelectionTest {

    private static PythonOptimisationResponse responseWith(
            String recommendedScenarioId,
            List<Map<String, Object>> candidates
    ) {
        return new PythonOptimisationResponse(
                "req-1", "success", "Balanced", Map.of(), Map.of(), Map.of(), "SUCCESS",
                candidates,
                recommendedScenarioId != null
                        ? Map.of("recommended_scenario_id", recommendedScenarioId)
                        : null,
                Map.of(), List.of());
    }

    private static Map<String, Object> candidate(String scenarioId, String segmentId, String cableId) {
        return Map.of(
                "scenario_id", scenarioId,
                "cable_sizing", Map.of(
                        "assignments", List.of(Map.of(
                                "segment_id", segmentId,
                                "selected_cable_type_id", cableId,
                                "required_current_a", 210.5,
                                "effective_ampacity_a", 400.0,
                                "utilization_fraction", 0.526))));
    }

    @Test
    void readsTheConductorChosenForEachSegment() {
        var selections = CableSelection.fromResponse(
                responseWith("SC-1", List.of(candidate("SC-1", "SEG-FDR001-0001", "AL-240"))));

        assertThat(selections).containsOnlyKeys("SEG-FDR001-0001");
        CableSelection cable = selections.get("SEG-FDR001-0001");
        assertThat(cable.cableTypeId()).isEqualTo("AL-240");
        assertThat(cable.requiredCurrentA()).isEqualByComparingTo("210.50");
        assertThat(cable.effectiveAmpacityA()).isEqualByComparingTo("400.00");
        // Reported as a percentage, because "0.526" on an engineering schedule invites being read
        // as half a percent.
        assertThat(cable.utilisationPct()).isEqualByComparingTo("52.60");
    }

    @Test
    void takesConductorsOnlyFromTheRecommendedCandidate() {
        // Every candidate carries its own sizing. Attributing a rejected network's conductors to
        // the segments actually being built would be wrong in a way that reads as plausible.
        var selections = CableSelection.fromResponse(responseWith("SC-2", List.of(
                candidate("SC-1", "SEG-1", "AL-120-REJECTED"),
                candidate("SC-2", "SEG-1", "AL-240-CHOSEN"))));

        assertThat(selections.get("SEG-1").cableTypeId()).isEqualTo("AL-240-CHOSEN");
    }

    @Test
    void reportsNothingRatherThanGuessingWhenNoCandidateIsRecommended() {
        var selections = CableSelection.fromResponse(
                responseWith(null, List.of(candidate("SC-1", "SEG-1", "AL-240"))));

        assertThat(selections)
                .as("with no recommendation there is no basis for choosing whose conductors to use")
                .isEmpty();
    }

    @Test
    void reportsNothingWhenTheRecommendationNamesAnAbsentCandidate() {
        var selections = CableSelection.fromResponse(
                responseWith("SC-MISSING", List.of(candidate("SC-1", "SEG-1", "AL-240"))));

        assertThat(selections).isEmpty();
    }

    /**
     * A run that produced no sizing must still persist its routes. Losing a whole network because
     * one optional field was absent would be a poor trade.
     */
    @Test
    void survivesResponsesCarryingNoSizingAtAll() {
        assertThat(CableSelection.fromResponse(responseWith("SC-1", List.of()))).isEmpty();
        assertThat(CableSelection.fromResponse(responseWith("SC-1", null))).isEmpty();
        assertThat(CableSelection.fromResponse(null)).isEmpty();
        assertThat(CableSelection.fromResponse(responseWith("SC-1",
                List.of(Map.of("scenario_id", "SC-1"))))).isEmpty();
    }

    @Test
    void skipsMalformedAssignmentsInsteadOfFailingTheRun() {
        Map<String, Object> candidate = Map.of(
                "scenario_id", "SC-1",
                "cable_sizing", Map.of("assignments", List.of(
                        Map.of("segment_id", "SEG-GOOD", "selected_cable_type_id", "AL-240",
                                "required_current_a", 100.0, "effective_ampacity_a", 400.0,
                                "utilization_fraction", 0.25),
                        Map.of("selected_cable_type_id", "AL-240"),
                        Map.of("segment_id", "SEG-NO-CABLE"),
                        "not even a map")));

        var selections = CableSelection.fromResponse(responseWith("SC-1", List.of(candidate)));

        assertThat(selections).containsOnlyKeys("SEG-GOOD");
    }

    @Test
    void toleratesMissingNumbersWithoutLosingTheConductor() {
        // The conductor identity is the part the bill of materials needs; the currents are
        // supporting detail and their absence must not discard the selection.
        Map<String, Object> candidate = Map.of(
                "scenario_id", "SC-1",
                "cable_sizing", Map.of("assignments", List.of(
                        Map.of("segment_id", "SEG-1", "selected_cable_type_id", "AL-240"))));

        CableSelection cable = CableSelection.fromResponse(
                responseWith("SC-1", List.of(candidate))).get("SEG-1");

        assertThat(cable.cableTypeId()).isEqualTo("AL-240");
        assertThat(cable.requiredCurrentA()).isNull();
        assertThat(cable.utilisationPct()).isNull();
    }
}
