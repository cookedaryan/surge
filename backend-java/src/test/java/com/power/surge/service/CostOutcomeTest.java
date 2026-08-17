package com.power.surge.service;

import com.power.surge.dto.client.python.PythonOptimisationResponse;
import org.junit.jupiter.api.Test;

import java.math.BigDecimal;
import java.util.ArrayList;
import java.util.HashMap;
import java.util.List;
import java.util.Map;

import static org.assertj.core.api.Assertions.assertThat;

/**
 * Reading the money the engine computed.
 *
 * <p>Since the optimiser has rates it prices every candidate. Nothing here read it, so every cost the
 * product displayed came from {@code route length × 80} — a constant with no basis, no currency and
 * no provenance.
 */
class CostOutcomeTest {

    private PythonOptimisationResponse responseWith(Map<String, Object> cost, String recommendedId) {
        Map<String, Object> candidate = new HashMap<>();
        candidate.put("scenario_id", "SCN-002");
        candidate.put("cost", cost);

        Map<String, Object> other = new HashMap<>();
        other.put("scenario_id", "SCN-001");
        other.put("cost", Map.of(
                "total_capex", 999_999.0,
                "currency", "USD",
                "line_items", List.of(Map.of(
                        "category", "conductor", "item_id", "SEG-1", "amount", 111_111.0))));

        Map<String, Object> recommendation = new HashMap<>();
        recommendation.put("recommended_scenario_id", recommendedId);

        return new PythonOptimisationResponse(
                "job-1", "success", "Balanced", Map.of(), Map.of(), Map.of(),
                "SUCCESS", List.of(other, candidate), recommendation, Map.of(), List.of());
    }

    private Map<String, Object> fullCost() {
        Map<String, Object> cost = new HashMap<>();
        cost.put("currency", "INR");
        cost.put("conductor_capex", 208_393.7877047831);
        cost.put("pole_capex", 188_000.0);
        cost.put("land_capex", 0.0);
        cost.put("total_capex", 396_393.78770478314);
        cost.put("annual_loss_energy_mwh", 16.426429075822686);
        cost.put("annual_loss_cost", 57_492.5);
        cost.put("present_value_opex", 613_719.6);
        cost.put("lifecycle_cost", 1_010_113.38);
        cost.put("catalogue_id", "IN-33KV-INDICATIVE");
        cost.put("catalogue_version", "2026.1");
        cost.put("catalogue_price_basis_date", "2026-01-01");
        cost.put("failures", List.of());
        cost.put("line_items", List.of(
                Map.of("category", "conductor", "item_id", "SEG-FDR001-0001", "amount", 104_196.89),
                Map.of("category", "conductor", "item_id", "SEG-FDR001-0002", "amount", 104_196.90),
                Map.of("category", "pole", "item_id", "terminal", "amount", 90_000.0),
                Map.of("category", "opex", "item_id", "electrical_losses_pv", "amount", 613_719.6)));
        return cost;
    }

    @Test
    void readsTheWholeBreakdownFromTheRecommendedCandidate() {
        CostOutcome cost = CostOutcome.fromResponse(responseWith(fullCost(), "SCN-002"));

        assertThat(cost.currency()).isEqualTo("INR");
        assertThat(cost.conductorCapex()).isEqualByComparingTo("208393.79");
        assertThat(cost.poleCapex()).isEqualByComparingTo("188000.00");
        assertThat(cost.totalCapex()).isEqualByComparingTo("396393.79");
        assertThat(cost.lifecycleCost()).isEqualByComparingTo("1010113.38");
        // Kept at four places: losses in MWh are small numbers where two would round the difference
        // between candidates away.
        assertThat(cost.annualLossEnergyMwh()).isEqualByComparingTo("16.4264");
        assertThat(cost.catalogueId()).isEqualTo("IN-33KV-INDICATIVE");
        assertThat(cost.catalogueVersion()).isEqualTo("2026.1");
        assertThat(cost.priceBasisDate()).isEqualTo("2026-01-01");
        assertThat(cost.isAbsent()).isFalse();
    }

    @Test
    void takesOnlyTheConductorLineItemsPerSegment() {
        CostOutcome cost = CostOutcome.fromResponse(responseWith(fullCost(), "SCN-002"));

        // Pole and opex lines are keyed by class and by concept, not by segment. Letting either in
        // would attribute a pole class's whole cost to whichever route shared its id.
        assertThat(cost.conductorCostBySegment())
                .containsOnlyKeys("SEG-FDR001-0001", "SEG-FDR001-0002");
        assertThat(cost.conductorCostBySegment().get("SEG-FDR001-0001"))
                .isEqualByComparingTo("104196.89");
    }

    @Test
    void sumsRepeatedSegmentsRatherThanKeepingTheLastOne() {
        Map<String, Object> cost = fullCost();
        cost.put("line_items", List.of(
                Map.of("category", "conductor", "item_id", "SEG-1", "amount", 100.0),
                Map.of("category", "conductor", "item_id", "SEG-1", "amount", 50.0)));

        assertThat(CostOutcome.fromResponse(responseWith(cost, "SCN-002")).conductorCostBySegment())
                .containsEntry("SEG-1", new BigDecimal("150.00"));
    }

    @Test
    void ignoresTheCostsOfCandidatesThatWereNotChosen() {
        // SCN-001 is priced at 999,999 USD. Attributing a rejected network's money to the one being
        // built would be wrong in a way that looks entirely plausible in a report.
        CostOutcome cost = CostOutcome.fromResponse(responseWith(fullCost(), "SCN-002"));

        assertThat(cost.currency()).isEqualTo("INR");
        assertThat(cost.totalCapex()).isEqualByComparingTo("396393.79");
        assertThat(cost.conductorCostBySegment()).doesNotContainKey("SEG-1");
    }

    @Test
    void reportsNothingWhenNoCandidateWasRecommended() {
        // Falling back to the first candidate would be a guess, and a guess about which network's
        // money this is has no honest reading.
        CostOutcome cost = CostOutcome.fromResponse(responseWith(fullCost(), null));

        assertThat(cost.isAbsent()).isTrue();
        assertThat(cost.totalCapex()).isNull();
    }

    @Test
    void reportsNothingWhenTheRunCarriedNoCostAtAll() {
        Map<String, Object> candidate = new HashMap<>();
        candidate.put("scenario_id", "SCN-001");
        candidate.put("cost", null);
        PythonOptimisationResponse response = new PythonOptimisationResponse(
                "job-1", "success", "Balanced", Map.of(), Map.of(), Map.of(), "SUCCESS",
                List.of(candidate), Map.of("recommended_scenario_id", "SCN-001"), Map.of(), List.of());

        CostOutcome cost = CostOutcome.fromResponse(response);

        assertThat(cost.isAbsent()).isTrue();
        assertThat(cost.conductorCostBySegment()).isEmpty();
        // Absent, not zero: a run with no catalogue has no cost, and 0 reads as free.
        assertThat(cost.totalCapex()).isNull();
        assertThat(cost.lifecycleCost()).isNull();
    }

    @Test
    void keepsAPartialBreakdownAndCountsWhatCouldNotBePriced() {
        // The engine leaves a component null rather than costing a gap at zero, so a non-zero failure
        // count is what separates a total from a partial sum. Both have to survive.
        Map<String, Object> cost = new HashMap<>();
        cost.put("currency", "INR");
        cost.put("pole_capex", 188_000.0);
        cost.put("conductor_capex", null);
        cost.put("total_capex", null);
        cost.put("failures", List.of(
                Map.of("code", "CABLE_COST_NOT_FOUND", "component", "conductor_capex")));

        CostOutcome outcome = CostOutcome.fromResponse(responseWith(cost, "SCN-002"));

        assertThat(outcome.poleCapex()).isEqualByComparingTo("188000.00");
        assertThat(outcome.conductorCapex()).isNull();
        assertThat(outcome.totalCapex()).isNull();
        assertThat(outcome.failureCount()).isEqualTo(1);
    }

    @Test
    void survivesMalformedLineItems() {
        Map<String, Object> cost = fullCost();
        List<Object> items = new ArrayList<>();
        items.add("not a map");
        items.add(Map.of("category", "conductor"));
        items.add(new HashMap<>(Map.of("category", "conductor", "item_id", "SEG-9")));
        items.add(Map.of("category", "conductor", "item_id", "SEG-OK", "amount", 42.0));
        items.add(Map.of("category", "conductor", "item_id", "SEG-NAN", "amount", Double.NaN));
        cost.put("line_items", items);

        // A malformed optional field must not cost the run its routes.
        assertThat(CostOutcome.fromResponse(responseWith(cost, "SCN-002")).conductorCostBySegment())
                .containsOnlyKeys("SEG-OK");
    }

    @Test
    void uncostedIsAbsentByDefinition() {
        assertThat(CostOutcome.uncosted().isAbsent()).isTrue();
        assertThat(CostOutcome.fromResponse(null).isAbsent()).isTrue();
    }
}
