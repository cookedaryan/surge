package com.power.surge.service;

import com.power.surge.domain.CableDataProvenance;
import com.power.surge.domain.CableType;
import com.power.surge.repository.CableTypeRepository;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.Mock;
import org.mockito.junit.jupiter.MockitoExtension;
import org.springframework.test.util.ReflectionTestUtils;

import java.math.BigDecimal;
import java.util.List;
import java.util.Map;

import static org.assertj.core.api.Assertions.assertThat;
import static org.mockito.Mockito.when;

/**
 * This service decides which conductors every run is allowed to consider, so it sits underneath
 * every electrical figure the system produces — losses, voltage drop, segment utilisation.
 *
 * <p>The shape it emits is consumed by Python's {@code CableConfigRequest}, which validates it
 * strictly: at least one cable type, a default that names one of them, and
 * {@code min_voltage_pu < max_voltage_pu} with both above zero. A config that violates any of those
 * is rejected at the boundary and the whole run fails, so the tests below pin the contract rather
 * than the implementation.
 */
@ExtendWith(MockitoExtension.class)
class CableCatalogueServiceTest {

    private static final BigDecimal KV_33 = new BigDecimal("33.00");

    @Mock
    private CableTypeRepository cableTypeRepository;

    private CableCatalogueService service;

    @BeforeEach
    void setUp() {
        service = new CableCatalogueService(cableTypeRepository);
    }

    /** Built by reflection because the entity is JPA-managed and exposes no setters. */
    private static CableType cable(String id, double maxCurrentA, int parallelCount, CableDataProvenance provenance) {
        CableType cable = new CableType() {
        };
        ReflectionTestUtils.setField(cable, "cableTypeId", id);
        ReflectionTestUtils.setField(cable, "displayName", id);
        ReflectionTestUtils.setField(cable, "nominalVoltageKv", KV_33);
        ReflectionTestUtils.setField(cable, "resistanceOhmPerKm", new BigDecimal("0.27920"));
        ReflectionTestUtils.setField(cable, "reactanceOhmPerKm", new BigDecimal("0.35600"));
        ReflectionTestUtils.setField(cable, "capacitanceNfPerKm", new BigDecimal("9.700"));
        ReflectionTestUtils.setField(cable, "maxCurrentA", BigDecimal.valueOf(maxCurrentA));
        ReflectionTestUtils.setField(cable, "parallelCount", parallelCount);
        ReflectionTestUtils.setField(cable, "deratingFactor", new BigDecimal("0.900"));
        ReflectionTestUtils.setField(cable, "dataProvenance", provenance);
        return cable;
    }

    private void givenCatalogue(CableType... cables) {
        when(cableTypeRepository.findAllByNominalVoltageKvAndEnabledTrueOrderByMaxCurrentAAsc(KV_33))
                .thenReturn(List.of(cables));
    }

    @SuppressWarnings("unchecked")
    private static List<Map<String, Object>> cableTypesIn(Map<String, Object> config) {
        return (List<Map<String, Object>>) config.get("cable_types");
    }

    // --- falling back safely --------------------------------------------

    /**
     * An empty catalogue must produce null, not an empty config.
     *
     * <p>Python requires at least one cable type, so an empty config would be rejected and take the
     * whole run with it. Null instead means the engine synthesises its compatibility conductor and
     * the run still completes — on placeholder impedances, which the report says plainly. A run on
     * a placeholder is worth more than no run.
     */
    @Test
    void anEmptyCatalogueLeavesTheEngineOnItsCompatibilityConductor() {
        givenCatalogue();

        assertThat(service.buildCableConfig(KV_33, new BigDecimal("5.00"))).isNull();
    }

    @Test
    void aCatalogueWithNothingAtThisVoltageAlsoFallsBack() {
        // A 66 kV project against a 33 kV-only catalogue must not be given 33 kV conductors.
        when(cableTypeRepository.findAllByNominalVoltageKvAndEnabledTrueOrderByMaxCurrentAAsc(
                new BigDecimal("66.00"))).thenReturn(List.of());

        assertThat(service.buildCableConfig(new BigDecimal("66.00"), new BigDecimal("5.00"))).isNull();
    }

    // --- the config Python will accept ----------------------------------

    @Test
    void offersEveryConductorAndDefaultsToTheLargest() {
        givenCatalogue(
                cable("WEASEL", 150, 1, CableDataProvenance.INDICATIVE),
                cable("DOG", 290, 1, CableDataProvenance.INDICATIVE),
                cable("PANTHER", 470, 1, CableDataProvenance.INDICATIVE));

        Map<String, Object> config = service.buildCableConfig(KV_33, new BigDecimal("5.00"));

        assertThat(cableTypesIn(config)).extracting(c -> c.get("cable_type_id"))
                .containsExactly("WEASEL", "DOG", "PANTHER");
        // Sizing steps down from a conductor that can certainly carry the load. Defaulting to the
        // smallest would make the common case a failure to be recovered from.
        assertThat(config).containsEntry("default_cable_type_id", "PANTHER");
    }

    @Test
    void theDefaultAlwaysNamesAnOfferedConductor() {
        // Python rejects a default that is not in the list, which fails the run at the boundary.
        givenCatalogue(
                cable("A", 150, 1, CableDataProvenance.INDICATIVE),
                cable("B", 470, 1, CableDataProvenance.INDICATIVE));

        Map<String, Object> config = service.buildCableConfig(KV_33, new BigDecimal("5.00"));

        assertThat(cableTypesIn(config)).extracting(c -> c.get("cable_type_id"))
                .contains(config.get("default_cable_type_id"));
    }

    @Test
    void carriesEveryElectricalParameterTheLoadFlowNeeds() {
        givenCatalogue(cable("DOG", 290, 1, CableDataProvenance.INDICATIVE));

        Map<String, Object> entry = cableTypesIn(service.buildCableConfig(KV_33, new BigDecimal("5.00"))).get(0);

        assertThat(entry).containsOnlyKeys(
                "cable_type_id", "resistance_ohm_per_km", "reactance_ohm_per_km",
                "capacitance_nf_per_km", "max_current_a", "parallel_count", "derating_factor");
        assertThat(entry).containsEntry("resistance_ohm_per_km", 0.2792);
        assertThat(entry).containsEntry("max_current_a", 290.0);
    }

    /**
     * Bundled conductors are the reason parallel_count has to survive.
     *
     * <p>Pandapower divides impedance by it, so a twin bundle relieves voltage drop as well as
     * raising ampacity. Dropping the field would silently turn a twin into a single and leave the
     * engine unable to solve heavy feeders.
     */
    @Test
    void preservesParallelCountAndDeratingForBundledConductors() {
        givenCatalogue(cable("TWIN-PANTHER", 470, 2, CableDataProvenance.INDICATIVE));

        Map<String, Object> entry = cableTypesIn(service.buildCableConfig(KV_33, new BigDecimal("5.00"))).get(0);

        assertThat(entry).containsEntry("parallel_count", 2);
        assertThat(entry).containsEntry("derating_factor", 0.9);
    }

    // --- voltage limits -------------------------------------------------

    @Test
    void derivesVoltageLimitsFromTheRunsOwnDropAllowance() {
        givenCatalogue(cable("DOG", 290, 1, CableDataProvenance.INDICATIVE));

        Map<String, Object> config = service.buildCableConfig(KV_33, new BigDecimal("5.00"));

        // Matching what the compatibility path did, so moving to a real catalogue does not
        // silently change the limits the load flow is judged against.
        assertThat((double) config.get("min_voltage_pu")).isCloseTo(0.95, within(1e-9));
        assertThat((double) config.get("max_voltage_pu")).isCloseTo(1.05, within(1e-9));
    }

    @Test
    void fallsBackToFivePercentWhenNoDropAllowanceIsGiven() {
        givenCatalogue(cable("DOG", 290, 1, CableDataProvenance.INDICATIVE));

        Map<String, Object> config = service.buildCableConfig(KV_33, null);

        assertThat((double) config.get("min_voltage_pu")).isCloseTo(0.95, within(1e-9));
    }

    /**
     * Python requires min_voltage_pu above zero, so an absurd allowance must be clamped rather than
     * producing a negative bound that fails validation.
     */
    @Test
    void clampsTheLowerBoundAboveZeroForAnAbsurdAllowance() {
        givenCatalogue(cable("DOG", 290, 1, CableDataProvenance.INDICATIVE));

        Map<String, Object> config = service.buildCableConfig(KV_33, new BigDecimal("150.00"));

        double min = (double) config.get("min_voltage_pu");
        double max = (double) config.get("max_voltage_pu");
        assertThat(min).isGreaterThan(0.0);
        assertThat(min).isLessThan(max);
    }

    @Test
    void reportsTheVoltageTheRunAsked() {
        givenCatalogue(cable("DOG", 290, 1, CableDataProvenance.INDICATIVE));

        assertThat(service.buildCableConfig(new BigDecimal("33.00"), new BigDecimal("5.00")))
                .containsEntry("nominal_voltage_kv", 33.0);
    }

    // --- provenance -----------------------------------------------------

    @Test
    void saysPlainlyWhenThereIsNoCatalogueAtAll() {
        givenCatalogue();

        assertThat(service.describeProvenance(KV_33))
                .contains("No catalogue")
                .contains("placeholder");
    }

    @Test
    void countsHowManyConductorsAreStillUnverified() {
        givenCatalogue(
                cable("A", 150, 1, CableDataProvenance.VERIFIED),
                cable("B", 290, 1, CableDataProvenance.INDICATIVE),
                cable("C", 470, 1, CableDataProvenance.UNKNOWN));

        // UNKNOWN counts as unverified alongside INDICATIVE: neither has been checked, and the
        // figures they produce look exactly as authoritative as verified ones.
        assertThat(service.describeProvenance(KV_33)).contains("2 of 3");
    }

    @Test
    void confirmsWhenEveryConductorHasBeenVerified() {
        givenCatalogue(
                cable("A", 150, 1, CableDataProvenance.VERIFIED),
                cable("B", 470, 1, CableDataProvenance.VERIFIED));

        assertThat(service.describeProvenance(KV_33))
                .contains("All 2")
                .contains("verified");
    }

    private static org.assertj.core.data.Offset<Double> within(double tolerance) {
        return org.assertj.core.data.Offset.offset(tolerance);
    }
}
