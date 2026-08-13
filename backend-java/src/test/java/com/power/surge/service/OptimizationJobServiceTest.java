package com.power.surge.service;

import com.fasterxml.jackson.databind.ObjectMapper;
import com.power.surge.client.PythonOptimizationClient;
import com.power.surge.domain.JobStatus;
import com.power.surge.domain.OptimizationJob;
import com.power.surge.domain.Project;
import com.power.surge.domain.Substation;
import com.power.surge.domain.WtgLocation;
import com.power.surge.domain.WtgStatus;
import com.power.surge.dto.client.python.PythonOptimisationRequest;
import com.power.surge.dto.client.python.PythonOptimisationResponse;
import com.power.surge.dto.job.CreateOptimizationJobRequest;
import com.power.surge.dto.job.OptimizationJobResponse;
import com.power.surge.repository.GeneratedRouteRepository;
import com.power.surge.repository.OptimizationJobRepository;
import com.power.surge.repository.ProjectRepository;
import com.power.surge.repository.SubstationRepository;
import com.power.surge.repository.WtgLocationRepository;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.locationtech.jts.geom.Coordinate;
import org.locationtech.jts.geom.GeometryFactory;
import org.locationtech.jts.geom.Point;
import org.locationtech.jts.geom.PrecisionModel;
import org.mockito.ArgumentCaptor;
import org.mockito.Mock;
import org.mockito.junit.jupiter.MockitoExtension;

import java.math.BigDecimal;
import java.util.List;
import java.util.Map;
import java.util.Optional;
import java.util.UUID;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;
import static org.mockito.ArgumentMatchers.any;
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
    private RouteService routeService;

    @Mock
    private PoleService poleService;

    @Mock
    private PythonOptimizationClient pythonClient;

    @Mock
    private SseProgressService sseProgressService;

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
                routeService,
                poleService,
                pythonClient,
                new ObjectMapper(),
                sseProgressService
        );
    }

    @Test
    void createAndRunJob_success() {
        UUID projectId = UUID.randomUUID();
        Project project = new Project("Test Project", "Description");

        Point wtgPoint = geometryFactory.createPoint(new Coordinate(77.23, 28.63));
        WtgLocation wtg = new WtgLocation(project, "WTG-001", new BigDecimal("3.000"), wtgPoint);

        Point subPoint = geometryFactory.createPoint(new Coordinate(77.25, 28.64));
        Substation sub = new Substation(project, "SUB-001", new BigDecimal("100.000"), subPoint);

        when(projectRepository.findById(projectId)).thenReturn(Optional.of(project));
        when(wtgLocationRepository.findAllByProjectIdOrderByExternalIdAsc(projectId)).thenReturn(List.of(wtg));
        when(substationRepository.findAllByProjectIdOrderByExternalIdAsc(projectId)).thenReturn(List.of(sub));

        when(jobRepository.save(any(OptimizationJob.class))).thenAnswer(invocation -> invocation.getArgument(0));

        PythonOptimisationResponse pythonResponse = new PythonOptimisationResponse(
                "job-123", "success", "Balanced", Map.of(), Map.of(), Map.of("feeder_count", 1, "total_length_m", 1500.0)
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
     * Guard rail for the KMZ classification fix: evacuation towers live in their own table and never
     * reach this service, and turbine locations whose micro-siting status excludes them must not be
     * sent to the optimiser either. In the reference Uravakonda file only 38 of 99 turbine locations
     * are optimisable — sending all 99 would inflate the feeder count and distort the MST.
     */
    @Test
    void createAndRunJob_sendsOnlyOptimisableTurbinesToThePythonEngine() {
        UUID projectId = UUID.randomUUID();
        Project project = new Project("Uravakonda", "PCN route");

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
        when(jobRepository.save(any(OptimizationJob.class))).thenAnswer(invocation -> invocation.getArgument(0));
        when(pythonClient.runOptimization(any(PythonOptimisationRequest.class))).thenReturn(
                new PythonOptimisationResponse("job-1", "success", "Balanced", Map.of(), Map.of(),
                        Map.of("feeder_count", 1, "total_length_m", 1500.0)));

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
}
