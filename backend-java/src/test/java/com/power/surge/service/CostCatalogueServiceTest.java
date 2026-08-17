package com.power.surge.service;

import com.power.surge.domain.CableDataProvenance;
import com.power.surge.domain.CableType;
import com.power.surge.domain.ConductorCostItem;
import com.power.surge.domain.CostCatalogue;
import com.power.surge.domain.PoleCostItem;
import com.power.surge.repository.CableTypeRepository;
import com.power.surge.repository.CostCatalogueRepository;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.Mock;
import org.mockito.junit.jupiter.MockitoExtension;
import org.springframework.test.util.ReflectionTestUtils;

import java.math.BigDecimal;
import java.time.LocalDate;
import java.util.List;
import java.util.Map;

import static org.assertj.core.api.Assertions.assertThat;
import static org.mockito.Mockito.when;

/**
 * The rates a run is costed against, and how honestly their limits are reported.
 *
 * <p>Python computes CAPEX, land cost, loss valuation and a lifecycle total only for a request
 * carrying a {@code costing_config}. Java never sent one, so every candidate came back
 * {@code cost: null} while the UI displayed money derived from {@code route length × 80}.
 */
@ExtendWith(MockitoExtension.class)
class CostCatalogueServiceTest {

    @Mock private CostCatalogueRepository costCatalogueRepository;
    @Mock private CableTypeRepository cableTypeRepository;

    private CostCatalogueService service;

    @BeforeEach
    void setUp() {
        service = new CostCatalogueService(costCatalogueRepository, cableTypeRepository);
    }

    private CostCatalogue catalogue(CableDataProvenance itemProvenance, String... pricedConductors) {
        CostCatalogue c = new CostCatalogue();
        set(c, "catalogueId", "IN-33KV-INDICATIVE");
        set(c, "version", "2026.1");
        set(c, "currency", "INR");
        set(c, "priceBasisDate", LocalDate.of(2026, 1, 1));
        set(c, "landFixedCostPerParcel", new BigDecimal("25000.00"));
        set(c, "landVariableBasis", "ROUTE_OVERLAP_LENGTH_M");
        set(c, "landVariableRate", new BigDecimal("400.0000"));
        set(c, "analysisPeriodYears", 25);
        set(c, "discountRate", new BigDecimal("0.0800"));
        set(c, "annualOperatingHours", 8760);
        set(c, "lossLoadFactor", new BigDecimal("0.3500"));
        set(c, "energyPricePerMwh", new BigDecimal("3500.00"));
        set(c, "energyPriceBasisDate", LocalDate.of(2026, 1, 1));
        set(c, "dataProvenance", CableDataProvenance.INDICATIVE);

        for (String cableTypeId : pricedConductors) {
            ConductorCostItem item = new ConductorCostItem();
            set(item, "cableTypeId", cableTypeId);
            set(item, "installedCostPerKmPerCircuit", new BigDecimal("1350000.00"));
            set(item, "dataProvenance", itemProvenance);
            c.getConductorItems().add(item);
        }
        for (String poleType : List.of("terminal", "angle", "intermediate", "junction")) {
            PoleCostItem item = new PoleCostItem();
            set(item, "poleType", poleType);
            set(item, "installedCostEach", new BigDecimal("22000.00"));
            set(item, "dataProvenance", itemProvenance);
            c.getPoleItems().add(item);
        }
        return c;
    }

    /**
     * Built through the JPA constructor rather than mocked.
     *
     * <p>A Mockito stub cannot be created inline inside a {@code thenReturn(...)} argument — the
     * nested {@code when} reads as unfinished stubbing — and these are pure value holders anyway.
     */
    private CableType cable(String cableTypeId) {
        try {
            var constructor = CableType.class.getDeclaredConstructor();
            constructor.setAccessible(true);
            CableType cableType = constructor.newInstance();
            set(cableType, "cableTypeId", cableTypeId);
            return cableType;
        } catch (ReflectiveOperationException e) {
            throw new IllegalStateException("CableType has no no-arg constructor to build from", e);
        }
    }

    private void set(Object target, String field, Object value) {
        ReflectionTestUtils.setField(target, field, value);
    }

    @Test
    void buildsTheConfigInTheShapePythonValidates() {
        when(costCatalogueRepository.findEnabledWithItems())
                .thenReturn(List.of(catalogue(CableDataProvenance.INDICATIVE, "ACSR-DOG")));

        Map<String, Object> config = service.buildCostingConfig();

        assertThat(config).containsOnlyKeys("catalogue", "lifecycle");

        @SuppressWarnings("unchecked")
        Map<String, Object> catalogueNode = (Map<String, Object>) config.get("catalogue");
        assertThat(catalogueNode).containsEntry("catalogue_id", "IN-33KV-INDICATIVE")
                .containsEntry("currency", "INR")
                // A string, not a LocalDate: Python parses the ISO form, and Jackson would otherwise
                // serialise a date however it happens to be configured.
                .containsEntry("price_basis_date", "2026-01-01");

        @SuppressWarnings("unchecked")
        List<Map<String, Object>> conductorItems =
                (List<Map<String, Object>>) catalogueNode.get("conductor_items");
        // The key Python reads is per *parallel circuit*, and the engine multiplies by
        // parallel_count. Naming it anything else silently costs nothing.
        assertThat(conductorItems).singleElement().satisfies(item ->
                assertThat(item).containsEntry("cable_type_id", "ACSR-DOG")
                        .containsEntry("installed_cost_per_km_per_parallel_circuit", 1_350_000.0));

        @SuppressWarnings("unchecked")
        List<Map<String, Object>> poleItems = (List<Map<String, Object>>) catalogueNode.get("pole_items");
        assertThat(poleItems).hasSize(4);
        assertThat(poleItems).allSatisfy(item ->
                assertThat(item.get("pole_type").toString())
                        .as("Python validates the lowercase vocabulary")
                        .isLowerCase());

        @SuppressWarnings("unchecked")
        Map<String, Object> lifecycle = (Map<String, Object>) config.get("lifecycle");
        assertThat(lifecycle).containsEntry("analysis_period_years", 25)
                .containsEntry("discount_rate", 0.08)
                .containsEntry("annual_operating_hours", 8760)
                .containsEntry("loss_load_factor", 0.35)
                .containsEntry("energy_price_per_mwh", 3500.0)
                // Both halves must agree, because nothing in the system converts currencies.
                .containsEntry("currency", catalogueNode.get("currency"));
    }

    @Test
    void sendsNothingWhenNoCatalogueIsConfigured() {
        when(costCatalogueRepository.findEnabledWithItems()).thenReturn(List.of());

        assertThat(service.buildCostingConfig())
                .as("an uncosted run is honest; a run priced against absent rates is not")
                .isNull();
    }

    @Test
    void sendsNothingWhenACatalogueHasNoConductorRates() {
        // Python prices what it can and voids the total, so a half-filled catalogue buys nothing but
        // a report with pole costs and no bottom line.
        when(costCatalogueRepository.findEnabledWithItems())
                .thenReturn(List.of(catalogue(CableDataProvenance.INDICATIVE)));

        assertThat(service.buildCostingConfig()).isNull();
    }

    @Test
    void namesConductorsTheCostCatalogueDoesNotPrice() {
        when(costCatalogueRepository.findEnabledWithItems())
                .thenReturn(List.of(catalogue(CableDataProvenance.INDICATIVE, "ACSR-DOG")));
        when(cableTypeRepository.findAllByEnabledTrueOrderByMaxCurrentAAsc())
                .thenReturn(List.of(cable("ACSR-DOG"), cable("ACSR-PANTHER"), cable("ACSR-WEASEL")));

        // The run picks the conductor, so one unpriced entry is enough to void every total. A
        // catalogue can be internally complete and still cover nothing the run selects.
        assertThat(service.conductorsWithoutRates())
                .containsExactly("ACSR-PANTHER", "ACSR-WEASEL");
    }

    @Test
    void describesUnverifiedRatesAsUnfitForCommittingMoney() {
        when(costCatalogueRepository.findEnabledWithItems())
                .thenReturn(List.of(catalogue(CableDataProvenance.INDICATIVE, "ACSR-DOG")));
        when(cableTypeRepository.findAllByEnabledTrueOrderByMaxCurrentAAsc())
                .thenReturn(List.of(cable("ACSR-DOG")));

        String provenance = service.describeProvenance();

        assertThat(provenance).contains("IN-33KV-INDICATIVE", "INR", "2026-01-01");
        assertThat(provenance).contains("5 of 5 rates are unverified");
        assertThat(provenance)
                .as("an indicative total looks exactly as authoritative as a tendered one")
                .contains("not for committing money");
    }

    @Test
    void describesAFullyVerifiedCatalogueWithoutTheCaveat() {
        when(costCatalogueRepository.findEnabledWithItems())
                .thenReturn(List.of(catalogue(CableDataProvenance.VERIFIED, "ACSR-DOG")));
        when(cableTypeRepository.findAllByEnabledTrueOrderByMaxCurrentAAsc())
                .thenReturn(List.of(cable("ACSR-DOG")));

        String provenance = service.describeProvenance();

        assertThat(provenance).contains("All 5 rates verified.");
        assertThat(provenance).doesNotContain("not for committing money");
    }

    @Test
    void warnsInTheProvenanceWhenAConductorHasNoRate() {
        when(costCatalogueRepository.findEnabledWithItems())
                .thenReturn(List.of(catalogue(CableDataProvenance.INDICATIVE, "ACSR-DOG")));
        when(cableTypeRepository.findAllByEnabledTrueOrderByMaxCurrentAAsc())
                .thenReturn(List.of(cable("ACSR-DOG"), cable("ACSR-QUAD-PANTHER")));

        assertThat(service.describeProvenance())
                .contains("No rate for ACSR-QUAD-PANTHER")
                .contains("reports no total");
    }

    @Test
    void saysPlainlyWhenARunCarriesNoCostsAtAll() {
        when(costCatalogueRepository.findEnabledWithItems()).thenReturn(List.of());

        assertThat(service.describeProvenance()).isEqualTo(
                "No cost catalogue configured — this run carries no costs.");
        assertThat(service.activeCurrency()).isEmpty();
    }
}
