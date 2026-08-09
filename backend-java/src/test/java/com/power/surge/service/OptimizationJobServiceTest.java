package com.power.surge.service;

import com.fasterxml.jackson.databind.ObjectMapper;
import com.power.surge.client.PythonOptimizationClient;
import com.power.surge.domain.JobStatus;
import com.power.surge.domain.OptimizationJob;
import com.power.surge.domain.Project;
import com.power.surge.domain.Substation;
import com.power.surge.domain.WtgLocation;
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
                "job-123", "success", "Balanced", Map.of(), Map.of("feeder_count", 1, "total_length_m", 1500.0)
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
