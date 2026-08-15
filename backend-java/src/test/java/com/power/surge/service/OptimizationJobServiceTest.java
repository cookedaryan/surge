package com.power.surge.service;

import com.fasterxml.jackson.databind.ObjectMapper;
import com.power.surge.client.PythonOptimizationClient;
import com.power.surge.domain.CadastralParcel;
import com.power.surge.domain.JobStatus;
import com.power.surge.domain.OptimizationJob;
import com.power.surge.domain.Project;
import com.power.surge.domain.RestrictedArea;
import com.power.surge.domain.Substation;
import com.power.surge.domain.WtgLocation;
import com.power.surge.domain.WtgStatus;
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
import org.locationtech.jts.geom.LinearRing;
import org.locationtech.jts.geom.Point;
import org.locationtech.jts.geom.Polygon;
import org.locationtech.jts.geom.PrecisionModel;
import org.mockito.ArgumentCaptor;
import org.mockito.Mock;
import org.mockito.junit.jupiter.MockitoExtension;
import org.springframework.transaction.support.TransactionSynchronization;
import org.springframework.transaction.support.TransactionSynchronizationManager;

import java.math.BigDecimal;
import java.util.List;
import java.util.Map;
import java.util.Optional;
import java.util.UUID;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.ArgumentMatchers.anyBoolean;
import static org.mockito.ArgumentMatchers.anyString;
import static org.mockito.ArgumentMatchers.eq;
import static org.mockito.Mockito.never;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.when;

@ExtendWith(MockitoExtension.class)
class OptimizationJobServiceTest {

    @Mock
    private ProjectRepository projectRepository;

    @Mock
    private OptimizationJobRepository jobRepository;

    @Mock
    private GeneratedRouteRepository routeRepository;

    @Mock
    private WtgLocationRepository wtgLocationRepository;

    @Mock
    private SubstationRepository substationRepository;

    @Mock
    private ReferenceLineRepository referenceLineRepository;

    @Mock
    private CadastralParcelRepository parcelRepository;

    @Mock
    private RestrictedAreaRepository restrictedAreaRepository;

    @Mock
    private RouteService routeService;

    @Mock
    private PoleService poleService;

    @Mock
    private PythonOptimizationClient pythonClient;

    @Mock
    private SseProgressService sseProgressService;

    @Mock
    private AuditLogService auditLogService;

    private OptimizationJobService jobService;
    private final GeometryFactory geometryFactory = new GeometryFactory(new PrecisionModel(), Project.WGS84_SRID);

    @BeforeEach
    void setUp() {
        jobService = new OptimizationJobService(
                projectRepository,
                jobRepository,
                routeRepository,
                wtgLocationRepository,
                substationRepository,
                referenceLineRepository,
                parcelRepository,
                restrictedAreaRepository,
                routeService,
                poleService,
                pythonClient,
                new ObjectMapper(),
                sseProgressService,
                auditLogService
        );
    }

    /**
     * Models how the job round-trips through storage: a save assigns an id, and the run reads the
     * job back by that id. Jobs are queued and executed separately now, so the execution half only
     * has the persisted row to work from.
     */
    private void stubJobPersistence() {
        OptimizationJob[] saved = new OptimizationJob[1];
        when(jobRepository.save(any(OptimizationJob.class))).thenAnswer(inv -> {
            OptimizationJob job = inv.getArgument(0);
            if (job.getId() == null) {
                org.springframework.test.util.ReflectionTestUtils.setField(job, "id", UUID.randomUUID());
            }
            saved[0] = job;
            return job;
        });
        when(jobRepository.findById(any(UUID.class)))
                .thenAnswer(inv -> java.util.Optional.ofNullable(saved[0]));
    }

    @Test
    void createAndRunJob_success() {
        UUID projectId = UUID.randomUUID();
        Project project = new Project("Test Project", "Description");
        // A persisted project has an id; the run reads it back off the job entity.
        org.springframework.test.util.ReflectionTestUtils.setField(project, "id", projectId);

        Point wtgPoint = geometryFactory.createPoint(new Coordinate(77.23, 28.63));
        WtgLocation wtg = new WtgLocation(project, "WTG-001", new BigDecimal("3.000"), wtgPoint);

        Point subPoint = geometryFactory.createPoint(new Coordinate(77.25, 28.64));
        Substation sub = new Substation(project, "SUB-001", new BigDecimal("100.000"), subPoint);

        when(projectRepository.findById(projectId)).thenReturn(Optional.of(project));
        when(wtgLocationRepository.findAllByProjectIdOrderByExternalIdAsc(projectId)).thenReturn(List.of(wtg));
        when(substationRepository.findAllByProjectIdOrderByExternalIdAsc(projectId)).thenReturn(List.of(sub));

        stubJobPersistence();

        PythonOptimisationResponse pythonResponse = new PythonOptimisationResponse(
                "job-123", "success", "Balanced", Map.of(), Map.of(),
                Map.of("feeder_count", 1, "total_length_m", 1500.0),
                "SUCCESS", List.of(), Map.of(), Map.of(), List.of()
        );
        when(pythonClient.runOptimization(any(PythonOptimisationRequest.class))).thenReturn(pythonResponse);

        CreateOptimizationJobRequest request = new CreateOptimizationJobRequest(
                "MULTI_OBJECTIVE_A_STAR", "Balanced", null, null, null, null, null, null, null
        );

        OptimizationJobResponse response = jobService.createAndRunJob(projectId, request);

        assertThat(response).isNotNull();
        assertThat(response.status()).isEqualTo(JobStatus.COMPLETED);
        assertThat(response.algorithmType()).isEqualTo("MULTI_OBJECTIVE_A_STAR");
    }

    /**
     * The scenario selector used to be cosmetic: the label was stored and displayed, but no weight
     * or constraint cost ever reached Python, so all four scenarios returned identical routes. This
     * proves each scenario now dispatches a genuinely different optimisation request.
     */
    @Test
    void eachScenarioDispatchesADistinctOptimisationRequest() {
        UUID projectId = UUID.randomUUID();
        Project project = new Project("Uravakonda", "PCN route");
        // A persisted project has an id; the run reads it back off the job entity.
        org.springframework.test.util.ReflectionTestUtils.setField(project, "id", projectId);

        WtgLocation wtg = new WtgLocation(project, "WTG-001", new BigDecimal("3.000"),
                geometryFactory.createPoint(new Coordinate(77.10, 14.30)));
        Substation sub = new Substation(project, "SUB-001", new BigDecimal("100.000"),
                geometryFactory.createPoint(new Coordinate(77.25, 14.40)));
        CadastralParcel parcel = new CadastralParcel(project, "P-001", "Owner",
                new BigDecimal("100.00"), squareAt(77.15, 14.35));
        RestrictedArea restricted = new RestrictedArea(project, "Sanctuary", "ENVIRONMENTAL",
                new BigDecimal("30.00"), squareAt(77.20, 14.38));

        when(projectRepository.findById(projectId)).thenReturn(Optional.of(project));
        when(wtgLocationRepository.findAllByProjectIdOrderByExternalIdAsc(projectId)).thenReturn(List.of(wtg));
        when(substationRepository.findAllByProjectIdOrderByExternalIdAsc(projectId)).thenReturn(List.of(sub));
        when(parcelRepository.findAllByProjectIdOrderByParcelIdAsc(projectId)).thenReturn(List.of(parcel));
        when(restrictedAreaRepository.findAllByProjectIdOrderByNameAsc(projectId)).thenReturn(List.of(restricted));
        stubJobPersistence();
        when(pythonClient.runOptimization(any(PythonOptimisationRequest.class))).thenReturn(
                new PythonOptimisationResponse("job-1", "success", "Balanced", Map.of(), Map.of(),
                        Map.of("feeder_count", 1, "total_length_m", 1500.0),
                        "SUCCESS", List.of(), Map.of(), Map.of(), List.of()));

        List<String> scenarios = List.of(
                ScenarioProfile.BALANCED,
                ScenarioProfile.MINIMUM_COST,
                ScenarioProfile.MINIMUM_LAND_IMPACT,
                ScenarioProfile.MINIMUM_ENVIRONMENTAL_IMPACT);

        for (String scenario : scenarios) {
            jobService.createAndRunJob(projectId, new CreateOptimizationJobRequest(
                    "MULTI_OBJECTIVE_A_STAR", scenario, null, null, null, null, null, null, null));
        }

        ArgumentCaptor<PythonOptimisationRequest> captor =
                ArgumentCaptor.forClass(PythonOptimisationRequest.class);
        verify(pythonClient, org.mockito.Mockito.times(scenarios.size())).runOptimization(captor.capture());
        List<PythonOptimisationRequest> sent = captor.getAllValues();

        // Every request must be materially different from every other one, not just differently
        // labelled. Comparing weights + constraint payload together catches a regression in either
        // mechanism on its own.
        List<String> fingerprints = sent.stream()
                .map(r -> r.scoringWeights() + "|" + r.avoidanceGeojson())
                .distinct()
                .toList();
        assertThat(fingerprints).hasSize(scenarios.size());

        // Minimum Cost accepts land crossings more readily; Minimum Land Impact resists them.
        double balancedParcelCost = parcelCostIn(sent.get(0));
        assertThat(parcelCostIn(sent.get(1))).isLessThan(balancedParcelCost);
        assertThat(parcelCostIn(sent.get(2))).isGreaterThan(balancedParcelCost);

        // Hard exclusions cannot carry a cost, so the environmental scenario buys clearance instead.
        assertThat(restrictedBufferIn(sent.get(3))).isGreaterThan(restrictedBufferIn(sent.get(0)));

        // Minimum Cost is the only scenario that reweights scoring toward raw route length.
        assertThat((Double) sent.get(1).scoringWeights().get("route_length_weight"))
                .isGreaterThan((Double) sent.get(0).scoringWeights().get("route_length_weight"));
    }

    private Polygon squareAt(double lon, double lat) {
        double d = 0.01;
        LinearRing ring = geometryFactory.createLinearRing(new Coordinate[]{
                new Coordinate(lon, lat),
                new Coordinate(lon + d, lat),
                new Coordinate(lon + d, lat + d),
                new Coordinate(lon, lat + d),
                new Coordinate(lon, lat)
        });
        return geometryFactory.createPolygon(ring);
    }

    private static double parcelCostIn(PythonOptimisationRequest request) {
        return (Double) constraintProperties(request, "parcel").get("cost_weight");
    }

    private static double restrictedBufferIn(PythonOptimisationRequest request) {
        return (Double) constraintProperties(request, "restricted_area").get("buffer_m");
    }

    @SuppressWarnings("unchecked")
    private static Map<String, Object> constraintProperties(PythonOptimisationRequest request, String constraintType) {
        List<Map<String, Object>> features =
                (List<Map<String, Object>>) request.avoidanceGeojson().get("features");
        return features.stream()
                .map(f -> (Map<String, Object>) f.get("properties"))
                .filter(p -> constraintType.equals(p.get("constraint_type")))
                .findFirst()
                .orElseThrow(() -> new AssertionError("No " + constraintType + " constraint was sent"));
    }

    /**
     * Guard rail for the KMZ classification fix: evacuation towers live in their own table and never
     * reach this service, and turbine locations whose micro-siting status excludes them must not be
     * sent to the optimiser either. In the reference Uravakonda file only 38 of 99 turbine locations
     * are optimisable — sending all 99 would inflate the feeder count and distort the MST.
     */
    @Test
    void createAndRunJob_sendsOnlyOptimisableTurbinesToThePythonEngine() {
        UUID projectId = UUID.randomUUID();
        Project project = new Project("Uravakonda", "PCN route");
        // A persisted project has an id; the run reads it back off the job entity.
        org.springframework.test.util.ReflectionTestUtils.setField(project, "id", projectId);

        WtgLocation approved = new WtgLocation(project, "KS67_S1", new BigDecimal("3.000"),
                geometryFactory.createPoint(new Coordinate(77.10, 14.30)), WtgStatus.APPROVED, "Site / Approved");
        WtgLocation cancelled = new WtgLocation(project, "KS82_S2", new BigDecimal("3.000"),
                geometryFactory.createPoint(new Coordinate(77.11, 14.31)), WtgStatus.CANCELLED, "Site / Cancel Location");
        WtgLocation lowAep = new WtgLocation(project, "KS37_S1", new BigDecimal("3.000"),
                geometryFactory.createPoint(new Coordinate(77.12, 14.32)), WtgStatus.LOW_AEP, "Site / Low AEP");

        Substation sub = new Substation(project, "SUB-001", new BigDecimal("100.000"),
                geometryFactory.createPoint(new Coordinate(77.25, 14.40)));

        when(projectRepository.findById(projectId)).thenReturn(Optional.of(project));
        when(wtgLocationRepository.findAllByProjectIdOrderByExternalIdAsc(projectId))
                .thenReturn(List.of(approved, cancelled, lowAep));
        when(substationRepository.findAllByProjectIdOrderByExternalIdAsc(projectId)).thenReturn(List.of(sub));
        stubJobPersistence();
        when(pythonClient.runOptimization(any(PythonOptimisationRequest.class))).thenReturn(
                new PythonOptimisationResponse("job-1", "success", "Balanced", Map.of(), Map.of(),
                        Map.of("feeder_count", 1, "total_length_m", 1500.0),
                        "SUCCESS", List.of(), Map.of(), Map.of(), List.of()));

        jobService.createAndRunJob(projectId, new CreateOptimizationJobRequest(
                "MULTI_OBJECTIVE_A_STAR", "Balanced", null, null, null, null, null, null, null));

        ArgumentCaptor<PythonOptimisationRequest> captor =
                ArgumentCaptor.forClass(PythonOptimisationRequest.class);
        verify(pythonClient).runOptimization(captor.capture());

        @SuppressWarnings("unchecked")
        List<Map<String, Object>> sentFeatures =
                (List<Map<String, Object>>) captor.getValue().wtgGeojson().get("features");

        assertThat(sentFeatures).hasSize(1);
        assertThat(sentFeatures.get(0).get("id")).isEqualTo("KS67_S1");
    }

    @Test
    void createAndRunJob_failsWhenEveryTurbineIsExcludedByStatus() {
        UUID projectId = UUID.randomUUID();
        Project project = new Project("Uravakonda", null);

        WtgLocation cancelled = new WtgLocation(project, "KS82_S2", new BigDecimal("3.000"),
                geometryFactory.createPoint(new Coordinate(77.11, 14.31)), WtgStatus.CANCELLED, null);

        when(projectRepository.findById(projectId)).thenReturn(Optional.of(project));
        when(wtgLocationRepository.findAllByProjectIdOrderByExternalIdAsc(projectId))
                .thenReturn(List.of(cancelled));

        assertThatThrownBy(() -> jobService.createAndRunJob(projectId, new CreateOptimizationJobRequest(
                "MULTI_OBJECTIVE_A_STAR", "Balanced", null, null, null, null, null, null, null)))
                .isInstanceOf(IllegalArgumentException.class)
                .hasMessageContaining("optimisable status");
    }

    @Test
    void createAndRunJob_failsWhenNoWtgs() {
        UUID projectId = UUID.randomUUID();
        Project project = new Project("Test Project", "Description");

        when(projectRepository.findById(projectId)).thenReturn(Optional.of(project));
        when(wtgLocationRepository.findAllByProjectIdOrderByExternalIdAsc(projectId)).thenReturn(List.of());

        CreateOptimizationJobRequest request = new CreateOptimizationJobRequest(
                "MULTI_OBJECTIVE_A_STAR", "Balanced", null, null, null, null, null, null, null
        );

        assertThatThrownBy(() -> jobService.createAndRunJob(projectId, request))
                .isInstanceOf(IllegalArgumentException.class)
                .hasMessageContaining("Project has no WTG locations");
    }

    /**
     * The whole pipeline runs in one transaction, so the routes and poles it writes are invisible to
     * every other connection until it commits. Announcing completion from inside that transaction
     * sent the browser off to fetch results nobody else could see yet: it got zero features back,
     * cached the empty answer, and left the map blank while the UI reported success.
     */
    @Test
    void completionIsAnnouncedOnlyAfterTheTransactionCommits() {
        UUID projectId = successfulRunFixture();

        TransactionSynchronizationManager.initSynchronization();
        try {
            jobService.createAndRunJob(projectId, new CreateOptimizationJobRequest(
                    "MULTI_OBJECTIVE_A_STAR", "Balanced", null, null, null, null, null, null, null));

            // Still inside the transaction: the results are written but not yet visible to anyone
            // else, so the client must not have been told to go and read them.
            verify(sseProgressService, never()).completeProgress(any(UUID.class), anyString(), anyBoolean());

            List<TransactionSynchronization> hooks =
                    TransactionSynchronizationManager.getSynchronizations();
            assertThat(hooks).hasSize(1);
            hooks.get(0).afterCompletion(TransactionSynchronization.STATUS_COMMITTED);

            verify(sseProgressService).completeProgress(
                    any(UUID.class), eq("Optimization job completed successfully!"), eq(true));
        } finally {
            TransactionSynchronizationManager.clearSynchronization();
        }
    }

    /**
     * A rollback must still close the stream. Reporting nothing would leave the client watching a
     * progress bar for work that no longer exists.
     */
    @Test
    void aRolledBackRunIsReportedAsFailedRatherThanLeftHanging() {
        UUID projectId = successfulRunFixture();

        TransactionSynchronizationManager.initSynchronization();
        try {
            jobService.createAndRunJob(projectId, new CreateOptimizationJobRequest(
                    "MULTI_OBJECTIVE_A_STAR", "Balanced", null, null, null, null, null, null, null));

            TransactionSynchronizationManager.getSynchronizations()
                    .get(0).afterCompletion(TransactionSynchronization.STATUS_ROLLED_BACK);

            verify(sseProgressService).completeProgress(
                    any(UUID.class),
                    eq("Optimization results could not be saved; the run was rolled back."),
                    eq(false));
        } finally {
            TransactionSynchronizationManager.clearSynchronization();
        }
    }

    /** A project the optimiser will run to completion over, returning one feeder. */
    private UUID successfulRunFixture() {
        UUID projectId = UUID.randomUUID();
        Project project = new Project("Test Project", "Description");
        org.springframework.test.util.ReflectionTestUtils.setField(project, "id", projectId);

        WtgLocation wtg = new WtgLocation(project, "WTG-001", new BigDecimal("3.000"),
                geometryFactory.createPoint(new Coordinate(77.23, 28.63)));
        Substation sub = new Substation(project, "SUB-001", new BigDecimal("100.000"),
                geometryFactory.createPoint(new Coordinate(77.25, 28.64)));

        when(projectRepository.findById(projectId)).thenReturn(Optional.of(project));
        when(wtgLocationRepository.findAllByProjectIdOrderByExternalIdAsc(projectId)).thenReturn(List.of(wtg));
        when(substationRepository.findAllByProjectIdOrderByExternalIdAsc(projectId)).thenReturn(List.of(sub));

        stubJobPersistence();

        when(pythonClient.runOptimization(any(PythonOptimisationRequest.class))).thenReturn(
                new PythonOptimisationResponse(
                        "job-123", "success", "Balanced", Map.of(), Map.of(),
                        Map.of("feeder_count", 1, "total_length_m", 1500.0),
                        "SUCCESS", List.of(), Map.of(), Map.of(), List.of()));

        return projectId;
    }
}
