package com.power.surge.service;

import com.fasterxml.jackson.databind.ObjectMapper;
import com.power.surge.client.PythonOptimizationClient;
import com.power.surge.domain.CadastralParcel;
import com.power.surge.domain.JobStatus;
import com.power.surge.domain.LineType;
import com.power.surge.domain.OptimizationJob;
import com.power.surge.domain.Project;
import com.power.surge.domain.ReferenceLine;
import com.power.surge.domain.RestrictedArea;
import com.power.surge.domain.Substation;
import com.power.surge.domain.WtgLocation;
import com.power.surge.dto.client.python.PythonOptimisationRequest;
import com.power.surge.dto.client.python.PythonOptimisationResponse;
import com.power.surge.dto.job.CreateOptimizationJobRequest;
import com.power.surge.dto.job.OptimizationJobResponse;
import com.power.surge.repository.CadastralParcelRepository;
import com.power.surge.repository.GeneratedRouteRepository;
import com.power.surge.repository.OptimizationJobRepository;
import com.power.surge.repository.ProjectRepository;
import com.power.surge.repository.ReferenceLineRepository;
import com.power.surge.repository.RestrictedAreaRepository;
import com.power.surge.repository.SubstationRepository;
import com.power.surge.repository.WtgLocationRepository;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.locationtech.jts.geom.Coordinate;
import org.locationtech.jts.geom.GeometryFactory;
import org.locationtech.jts.geom.LineString;
import org.locationtech.jts.geom.LinearRing;
import org.locationtech.jts.geom.Polygon;
import org.locationtech.jts.geom.PrecisionModel;
import org.mockito.ArgumentCaptor;
import org.mockito.Mock;
import org.mockito.junit.jupiter.MockitoExtension;
import org.springframework.test.util.ReflectionTestUtils;

import java.math.BigDecimal;
import java.util.List;
import java.util.Map;
import java.util.Optional;
import java.util.UUID;

import static org.assertj.core.api.Assertions.assertThat;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.ArgumentMatchers.eq;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.when;

/**
 * The Java-to-Python contract for one job.
 *
 * <p>Covers the two claims the delivery plan asks to be proven: that spatial constraints imported
 * into a project actually reach the optimiser, and that the route and pole output it returns stays
 * associated with the job that produced it. Both were previously only observable by running the
 * whole stack and reading a payload by hand.
 *
 * <p>This exercises the service boundary with mocked repositories. Verifying the rows actually
 * land in PostGIS needs a real database — H2 cannot create the {@code text[]} column on
 * {@code generated_poles} — so that remains a gap best closed with Testcontainers.
 */
@ExtendWith(MockitoExtension.class)
class OptimisationContractTest {

    @Mock private ProjectRepository projectRepository;
    @Mock private OptimizationJobRepository jobRepository;
    @Mock private GeneratedRouteRepository routeRepository;
    @Mock private WtgLocationRepository wtgLocationRepository;
    @Mock private SubstationRepository substationRepository;
    @Mock private ReferenceLineRepository referenceLineRepository;
    @Mock private CadastralParcelRepository parcelRepository;
    @Mock private RestrictedAreaRepository restrictedAreaRepository;
    @Mock private RouteService routeService;
    @Mock private PoleService poleService;
    @Mock private PythonOptimizationClient pythonClient;
    @Mock private SseProgressService sseProgressService;
    @Mock private AuditLogService auditLogService;
    @Mock private CableCatalogueService cableCatalogueService;
    @Mock private CostCatalogueService costCatalogueService;

    private OptimizationJobService jobService;
    private final GeometryFactory gf = new GeometryFactory(new PrecisionModel(), Project.WGS84_SRID);

    private static final UUID PROJECT_ID = UUID.randomUUID();
    private static final UUID JOB_ID = UUID.randomUUID();

    @BeforeEach
    void setUp() {
        jobService = new OptimizationJobService(
                projectRepository, jobRepository, routeRepository, wtgLocationRepository,
                substationRepository, referenceLineRepository, parcelRepository,
                restrictedAreaRepository, routeService, poleService, pythonClient,
                new ObjectMapper(), sseProgressService, auditLogService, cableCatalogueService,
                costCatalogueService);
    }

    private Polygon squareAt(double lon, double lat) {
        double d = 0.01;
        LinearRing ring = gf.createLinearRing(new Coordinate[]{
                new Coordinate(lon, lat), new Coordinate(lon + d, lat),
                new Coordinate(lon + d, lat + d), new Coordinate(lon, lat + d),
                new Coordinate(lon, lat)
        });
        return gf.createPolygon(ring);
    }

    private LineString lineAt(double lon, double lat) {
        return gf.createLineString(new Coordinate[]{
                new Coordinate(lon, lat), new Coordinate(lon + 0.02, lat + 0.02)
        });
    }

    /** A project carrying one of every constraint kind the importer can produce. */
    private Project givenFullyPopulatedProject(PythonOptimisationResponse response) {
        Project project = new Project("Uravakonda", "contract fixture");
        ReflectionTestUtils.setField(project, "id", PROJECT_ID);

        WtgLocation wtg = new WtgLocation(project, "WTG-001", new BigDecimal("3.000"),
                gf.createPoint(new Coordinate(77.10, 14.30)));
        Substation sub = new Substation(project, "SUB-001", new BigDecimal("100.000"),
                gf.createPoint(new Coordinate(77.25, 14.40)));

        when(projectRepository.findById(PROJECT_ID)).thenReturn(Optional.of(project));
        when(wtgLocationRepository.findAllByProjectIdOrderByExternalIdAsc(PROJECT_ID)).thenReturn(List.of(wtg));
        when(substationRepository.findAllByProjectIdOrderByExternalIdAsc(PROJECT_ID)).thenReturn(List.of(sub));
        when(referenceLineRepository.findAllByProjectIdOrderByExternalIdAsc(PROJECT_ID)).thenReturn(List.of(
                new ReferenceLine(project, "ROAD-1", LineType.ROAD, lineAt(77.12, 14.31)),
                new ReferenceLine(project, "HT-1", LineType.HT_LINE, lineAt(77.14, 14.33)),
                new ReferenceLine(project, "RIVER-1", LineType.WATERCOURSE, lineAt(77.16, 14.35)),
                // Carries no avoidance meaning and must not be sent as a constraint.
                new ReferenceLine(project, "EVAC-1", LineType.EVACUATION_ROUTE, lineAt(77.18, 14.37))
        ));
        when(parcelRepository.findAllByProjectIdOrderByParcelIdAsc(PROJECT_ID)).thenReturn(List.of(
                new CadastralParcel(project, "P-001", "Owner", new BigDecimal("100.00"), squareAt(77.15, 14.34))));
        when(restrictedAreaRepository.findAllByProjectIdOrderByNameAsc(PROJECT_ID)).thenReturn(List.of(
                new RestrictedArea(project, "Sanctuary", "ENVIRONMENTAL", new BigDecimal("30.00"),
                        squareAt(77.20, 14.38))));

        // A job is saved, then read back by id when it runs — the two halves are separate now.
        OptimizationJob[] persisted = new OptimizationJob[1];
        when(jobRepository.save(any(OptimizationJob.class))).thenAnswer(inv -> {
            OptimizationJob saved = inv.getArgument(0);
            if (saved.getId() == null) ReflectionTestUtils.setField(saved, "id", JOB_ID);
            persisted[0] = saved;
            return saved;
        });
        when(jobRepository.findById(any(UUID.class)))
                .thenAnswer(inv -> Optional.ofNullable(persisted[0]));
        when(pythonClient.runOptimization(any(PythonOptimisationRequest.class))).thenReturn(response);
        return project;
    }

    private static PythonOptimisationResponse successResponse() {
        return new PythonOptimisationResponse(
                "job-1", "success", "Balanced",
                Map.of("type", "FeatureCollection", "features", List.of(Map.of("type", "Feature"))),
                Map.of("type", "FeatureCollection", "features", List.of(Map.of("type", "Feature"))),
                Map.of("feeder_count", 1, "total_length_m", 1500.0),
                "SUCCESS", List.of(), Map.of(), Map.of(), List.of());
    }

    @SuppressWarnings("unchecked")
    private static List<Map<String, Object>> constraintFeatures(PythonOptimisationRequest request) {
        assertThat(request.avoidanceGeojson()).as("constraints must be sent").isNotNull();
        assertThat(request.avoidanceGeojson().get("type")).isEqualTo("FeatureCollection");
        return (List<Map<String, Object>>) request.avoidanceGeojson().get("features");
    }

    @SuppressWarnings("unchecked")
    private static Map<String, Object> propsOf(Map<String, Object> feature) {
        return (Map<String, Object>) feature.get("properties");
    }

    private PythonOptimisationRequest runAndCaptureRequest() {
        jobService.createAndRunJob(PROJECT_ID, new CreateOptimizationJobRequest(
                "MULTI_OBJECTIVE_A_STAR", "Balanced", null, null, null, null, null, null, null));
        ArgumentCaptor<PythonOptimisationRequest> captor =
                ArgumentCaptor.forClass(PythonOptimisationRequest.class);
        verify(pythonClient).runOptimization(captor.capture());
        return captor.getValue();
    }

    @Test
    void everyImportedConstraintKindReachesTheOptimiser() {
        givenFullyPopulatedProject(successResponse());

        List<Map<String, Object>> features = constraintFeatures(runAndCaptureRequest());

        assertThat(features.stream().map(f -> propsOf(f).get("constraint_type")))
                .containsExactlyInAnyOrder("road", "ht_line", "watercourse", "parcel", "restricted_area");
    }

    /**
     * The distinction the whole constraint model rests on: a restricted area must never be
     * crossed, whereas a road or a parcel may be crossed at a cost. Collapsing the two would
     * either make routing impossible or let a route run through a no-go zone.
     */
    @Test
    void restrictedAreasAreHardExclusionsAndEverythingElseIsSoft() {
        givenFullyPopulatedProject(successResponse());

        List<Map<String, Object>> features = constraintFeatures(runAndCaptureRequest());

        for (Map<String, Object> feature : features) {
            Map<String, Object> props = propsOf(feature);
            String type = String.valueOf(props.get("constraint_type"));
            if ("restricted_area".equals(type)) {
                assertThat(props.get("routing_mode")).isEqualTo("hard");
                // Python rejects a hard constraint that also carries a cost.
                assertThat(props).doesNotContainKey("cost_weight");
                assertThat(props.get("buffer_m")).isNotNull();
            } else {
                assertThat(props.get("routing_mode")).as("%s must be crossable", type).isEqualTo("soft");
                assertThat(props.get("cost_weight")).as("%s needs a cost", type).isNotNull();
            }
        }
    }

    @Test
    void referenceLinesWithNoAvoidanceMeaningAreNotSent() {
        givenFullyPopulatedProject(successResponse());

        List<Map<String, Object>> features = constraintFeatures(runAndCaptureRequest());

        assertThat(features.stream().map(f -> String.valueOf(propsOf(f).get("constraint_id"))))
                .as("evacuation routes are reference data, not obstacles")
                .noneMatch(id -> id.contains("EVAC"));
        assertThat(features).hasSize(5);
    }

    @Test
    void everyConstraintCarriesGeometryAndAStableIdentifier() {
        givenFullyPopulatedProject(successResponse());

        for (Map<String, Object> feature : constraintFeatures(runAndCaptureRequest())) {
            assertThat(feature.get("type")).isEqualTo("Feature");
            assertThat(feature.get("geometry")).isNotNull();
            assertThat(propsOf(feature).get("constraint_id")).isNotNull();
        }
    }

    @Test
    void theRequestAlsoCarriesTheAssetsAndTunablesTheRunDependsOn() {
        givenFullyPopulatedProject(successResponse());

        PythonOptimisationRequest request = runAndCaptureRequest();

        assertThat(request.projectId()).isEqualTo(PROJECT_ID.toString());
        assertThat(request.wtgGeojson()).isNotNull();
        assertThat(request.substationGeojson()).isNotNull();
        assertThat(request.poleConfig()).containsKey("max_span_m");
        assertThat(request.scoringWeights()).containsKey("route_length_weight");
        assertThat(request.electricalParams()).containsEntry("nominal_voltage_kv", 33.0);
    }

    /** Route and pole output must be filed against the job that produced it, never another. */
    @Test
    void returnedRoutesAndPolesArePersistedAgainstTheSameJob() {
        givenFullyPopulatedProject(successResponse());

        jobService.createAndRunJob(PROJECT_ID, new CreateOptimizationJobRequest(
                "MULTI_OBJECTIVE_A_STAR", "Balanced", null, null, null, null, null, null, null));

        verify(routeService).saveRoutesFromGeoJson(eq(JOB_ID), any(), any());
        verify(poleService).savePolesFromGeoJson(eq(JOB_ID), any());
    }

    // --- outcome contract, pinned ahead of the v1 -> v2 migration ------------
    //
    // These fix the *observable* result for each workflow status rather than any internal detail,
    // so they stay true if the migration preserves behaviour and fail loudly if it does not.
    //
    // The specific hazard: v1 collapses the workflow's four-value status into two, mapping both
    // SUCCESS and PARTIAL_SUCCESS to the literal "success" (`schemas/legacy_mapping.py:77`). v2
    // returns the four values raw. The service decides success with
    // `"success".equalsIgnoreCase(pythonResp.status())`, so a naive repoint at v2 would read
    // PARTIAL_SUCCESS as failure, mark the job FAILED and throw away routes and poles the
    // optimiser did produce.

    /**
     * A run that produced a usable network while falling short somewhere must keep that network.
     *
     * <p>Partial success is the normal outcome when one feeder cannot be solved but the rest can —
     * discarding the whole result would throw away work the operator can act on.
     */
    @Test
    void aPartiallySuccessfulRunStillPersistsWhatItProduced() {
        givenFullyPopulatedProject(new PythonOptimisationResponse(
                "job-1", "success", "Balanced",
                Map.of("type", "FeatureCollection", "features", List.of(Map.of("type", "Feature"))),
                Map.of("type", "FeatureCollection", "features", List.of(Map.of("type", "Feature"))),
                Map.of("feeder_count", 1, "total_length_m", 1500.0),
                "PARTIAL_SUCCESS", List.of(), Map.of(), Map.of(), List.of()));

        OptimizationJobResponse response = jobService.createAndRunJob(PROJECT_ID,
                new CreateOptimizationJobRequest(
                        "MULTI_OBJECTIVE_A_STAR", "Balanced", null, null, null, null, null, null, null));

        assertThat(response.status())
                .as("a partial result is still a result; the job must not be marked failed")
                .isEqualTo(JobStatus.COMPLETED);
        verify(routeService).saveRoutesFromGeoJson(eq(JOB_ID), any(), any());
        verify(poleService).savePolesFromGeoJson(eq(JOB_ID), any());
    }

    /**
     * A run has to record which rates it was costed against.
     *
     * <p>The catalogue can be re-rated after the fact, and a cost read against different rates from
     * the ones that produced it is not a cost at all. Storing the description with the job keeps the
     * two together.
     */
    @Test
    void theStoredSummaryRecordsWhichRatesTheRunWasCostedAgainst() {
        when(costCatalogueService.describeProvenance())
                .thenReturn("Costed against IN-33KV-INDICATIVE v2026.1 in INR, priced as at 2026-01-01. "
                        + "12 of 12 rates are unverified; these figures are for comparing scenarios, "
                        + "not for committing money.");
        givenFullyPopulatedProject(successResponse());

        OptimizationJobResponse response = jobService.createAndRunJob(PROJECT_ID,
                new CreateOptimizationJobRequest(
                        "MULTI_OBJECTIVE_A_STAR", "Balanced", null, null, null, null, null, null, null));

        assertThat(response.resultSummaryJson())
                .contains("costProvenance")
                .contains("IN-33KV-INDICATIVE")
                .contains("not for committing money");
    }

    /**
     * The run must ask for costs, or Python will not compute any.
     *
     * <p>Python calls its cost model only for a request carrying a {@code costing_config}. Java sent
     * none, so every candidate returned {@code cost: null} while the product displayed money derived
     * from {@code route length × 80}.
     */
    @Test
    void theRequestCarriesTheCostingConfigWhenACatalogueExists() {
        Map<String, Object> costingConfig = Map.of(
                "catalogue", Map.of("catalogue_id", "IN-33KV-INDICATIVE"),
                "lifecycle", Map.of("currency", "INR"));
        when(costCatalogueService.buildCostingConfig()).thenReturn(costingConfig);
        givenFullyPopulatedProject(successResponse());

        jobService.createAndRunJob(PROJECT_ID, new CreateOptimizationJobRequest(
                "MULTI_OBJECTIVE_A_STAR", "Balanced", null, null, null, null, null, null, null));

        ArgumentCaptor<PythonOptimisationRequest> sent =
                ArgumentCaptor.forClass(PythonOptimisationRequest.class);
        verify(pythonClient).runOptimization(sent.capture());
        assertThat(sent.getValue().costingConfig()).isEqualTo(costingConfig);
    }

    /** With no catalogue the field must be absent, not an empty object Python would reject. */
    @Test
    void theRequestOmitsTheCostingConfigWhenThereIsNoCatalogue() {
        when(costCatalogueService.buildCostingConfig()).thenReturn(null);
        givenFullyPopulatedProject(successResponse());

        jobService.createAndRunJob(PROJECT_ID, new CreateOptimizationJobRequest(
                "MULTI_OBJECTIVE_A_STAR", "Balanced", null, null, null, null, null, null, null));

        ArgumentCaptor<PythonOptimisationRequest> sent =
                ArgumentCaptor.forClass(PythonOptimisationRequest.class);
        verify(pythonClient).runOptimization(sent.capture());
        assertThat(sent.getValue().costingConfig()).isNull();
    }

    /**
     * Per-feeder results and the violations behind them have to survive into the stored summary.
     *
     * <p>The network-level electrical summary reports one loss figure and a violation *count*: it
     * says a limit was breached without saying which feeder breached it or by how much. On the
     * reference project one feeder sits at 1.055 pu while the network reads as valid, which is
     * exactly the case the totals cannot show.
     */
    @Test
    void theStoredSummaryKeepsPerFeederResultsAndViolations() {
        Map<String, Object> recommendedResult = Map.of(
                "network_summary", Map.of("feeder_count", 2),
                "electrical_summary", Map.of("converged", true, "valid", true, "violation_count", 1),
                "feeders", List.of(
                        Map.of("feeder_id", "FDR-001", "active_loss_mw", 0.4125,
                                "maximum_loading_percent", 90.4, "valid", true),
                        Map.of("feeder_id", "FDR-003", "active_loss_mw", 0.5176,
                                "maximum_voltage_pu", 1.055, "valid", false)),
                "violations", List.of(Map.of(
                        "code", "BUS_OVERVOLTAGE", "message", "bus above limit",
                        "node_id", "wtg:KS-51_S3", "measured_value", 1.06, "limit_value", 1.05)));

        givenFullyPopulatedProject(new PythonOptimisationResponse(
                "job-1", "success", "Balanced",
                Map.of("type", "FeatureCollection", "features", List.of(Map.of("type", "Feature"))),
                Map.of("type", "FeatureCollection", "features", List.of(Map.of("type", "Feature"))),
                Map.of("feeder_count", 2), "SUCCESS", List.of(), Map.of(),
                recommendedResult, List.of()));

        OptimizationJobResponse response = jobService.createAndRunJob(PROJECT_ID,
                new CreateOptimizationJobRequest(
                        "MULTI_OBJECTIVE_A_STAR", "Balanced", null, null, null, null, null, null, null));

        String summary = response.resultSummaryJson();
        assertThat(summary).as("the summary must carry the per-feeder results")
                .contains("\"feeders\"")
                .contains("FDR-003")
                .contains("1.055");
        assertThat(summary).as("and the violations behind the count")
                .contains("\"violations\"")
                .contains("BUS_OVERVOLTAGE")
                .contains("wtg:KS-51_S3");
    }

    /** A rejected run must not leave route or pole data behind from a network that was not chosen. */
    @Test
    void aFailedRunPersistsNoRoutesOrPoles() {
        givenFullyPopulatedProject(new PythonOptimisationResponse(
                "job-1", "failed", "Balanced", null, null, Map.of(),
                "NO_FEASIBLE_CANDIDATE", List.of(), Map.of(), Map.of(), List.of()));

        jobService.createAndRunJob(PROJECT_ID, new CreateOptimizationJobRequest(
                "MULTI_OBJECTIVE_A_STAR", "Balanced", null, null, null, null, null, null, null));

        verify(routeService, org.mockito.Mockito.never()).saveRoutesFromGeoJson(any(), any());
        verify(poleService, org.mockito.Mockito.never()).savePolesFromGeoJson(any(), any());
    }
}
