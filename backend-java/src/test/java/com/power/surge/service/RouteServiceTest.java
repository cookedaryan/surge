package com.power.surge.service;

import com.fasterxml.jackson.databind.ObjectMapper;
import com.power.surge.domain.GeneratedRoute;
import com.power.surge.domain.JobStatus;
import com.power.surge.domain.OptimizationJob;
import com.power.surge.domain.Project;
import com.power.surge.dto.route.CreateRouteRequest;
import com.power.surge.dto.route.GeneratedRouteResponse;
import com.power.surge.repository.GeneratedPoleRepository;
import com.power.surge.repository.GeneratedRouteRepository;
import com.power.surge.repository.OptimizationJobRepository;
import com.power.surge.repository.ProjectRepository;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.locationtech.jts.geom.Coordinate;
import org.locationtech.jts.geom.GeometryFactory;
import org.locationtech.jts.geom.LineString;
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
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.when;

@ExtendWith(MockitoExtension.class)
class RouteServiceTest {

    @Mock
    private ProjectRepository projectRepository;

    @Mock
    private OptimizationJobRepository jobRepository;

    @Mock
    private GeneratedRouteRepository routeRepository;

    @Mock
    private GeneratedPoleRepository poleRepository;

    private RouteService routeService;
    private final GeometryFactory geometryFactory = new GeometryFactory(new PrecisionModel(), Project.WGS84_SRID);

    @BeforeEach
    void setUp() {
        routeService = new RouteService(
                projectRepository,
                jobRepository,
                routeRepository,
                poleRepository,
                new ObjectMapper()
        );
    }

    @Test
    void saveRoutes_success() {
        UUID jobId = UUID.randomUUID();
        Project project = new Project("Test Project", "Description");
        OptimizationJob job = new OptimizationJob(project, "MULTI_OBJECTIVE_A_STAR", null, null, null, null);

        when(jobRepository.findById(jobId)).thenReturn(Optional.of(job));
        when(routeRepository.saveAll(any())).thenAnswer(invocation -> invocation.getArgument(0));

        CreateRouteRequest request = new CreateRouteRequest(
                "Feeder-01",
                new BigDecimal("2500.00"),
                new BigDecimal("150000.00"),
                new BigDecimal("12.5"),
                15,
                List.of(List.of(77.23, 28.63), List.of(77.25, 28.64)),
                null
        );

        List<GeneratedRouteResponse> responses = routeService.saveRoutes(jobId, List.of(request));

        assertThat(responses).hasSize(1);
        assertThat(responses.get(0).feederName()).isEqualTo("Feeder-01");
        assertThat(responses.get(0).totalLengthMeters()).isEqualByComparingTo("2500.00");
    }

    @Test
    void saveRoutesFromGeoJson_success() {
        UUID jobId = UUID.randomUUID();
        Project project = new Project("Test Project", "Description");
        OptimizationJob job = new OptimizationJob(project, "MULTI_OBJECTIVE_A_STAR", null, null, null, null);

        when(jobRepository.findById(jobId)).thenReturn(Optional.of(job));
        when(routeRepository.saveAll(any())).thenAnswer(invocation -> invocation.getArgument(0));

        Map<String, Object> geoJson = Map.of(
                "type", "FeatureCollection",
                "features", List.of(
                        Map.of(
                                "type", "Feature",
                                "geometry", Map.of(
                                        "type", "LineString",
                                        "coordinates", List.of(List.of(77.23, 28.63), List.of(77.25, 28.64))
                                ),
                                "properties", Map.of(
                                        "feederName", "Feeder-01",
                                        "totalLengthMeters", 2500.0,
                                        "poleCount", 15
                                )
                        )
                )
        );

        List<GeneratedRouteResponse> responses = routeService.saveRoutesFromGeoJson(jobId, geoJson);

        assertThat(responses).hasSize(1);
        assertThat(responses.get(0).feederName()).isEqualTo("Feeder-01");
        assertThat(responses.get(0).poleCount()).isEqualTo(15);
    }

    /**
     * A route the engine did not price must carry no cost.
     *
     * <p>This used to be {@code route length × 80}: a constant with no basis, no currency and no
     * provenance, which then flowed into the BOM total, the scenario comparison and the route popups
     * as though it were an estimate. On a 2.5 km segment it produced a confident $200,000.
     */
    @Test
    void saveRoutesFromGeoJson_doesNotFabricateACostFromLength() {
        UUID jobId = UUID.randomUUID();
        Project project = new Project("Test Project", "Description");
        OptimizationJob job = new OptimizationJob(project, "MULTI_OBJECTIVE_A_STAR", null, null, null, null);

        when(jobRepository.findById(jobId)).thenReturn(Optional.of(job));
        when(routeRepository.saveAll(any())).thenAnswer(invocation -> invocation.getArgument(0));

        Map<String, Object> geoJson = Map.of(
                "type", "FeatureCollection",
                "features", List.of(feature("Feeder-01", "SEG-1")));

        routeService.saveRoutesFromGeoJson(jobId, geoJson);

        @SuppressWarnings("unchecked")
        ArgumentCaptor<List<GeneratedRoute>> saved = ArgumentCaptor.forClass(List.class);
        verify(routeRepository).saveAll(saved.capture());
        GeneratedRoute route = saved.getValue().get(0);
        assertThat(route.getTotalCost())
                .as("2500 m used to become a confident 200,000 here")
                .isNull();
        assertThat(route.getConductorCost()).isNull();
        // The length itself is real and must survive: only the invented cost is gone.
        assertThat(route.getTotalLengthMeters()).isEqualByComparingTo("2500.0");
    }

    /** A cost the engine did report on the feature is still honoured. */
    @Test
    void saveRoutesFromGeoJson_keepsACostTheEngineSupplied() {
        UUID jobId = UUID.randomUUID();
        Project project = new Project("Test Project", "Description");
        OptimizationJob job = new OptimizationJob(project, "MULTI_OBJECTIVE_A_STAR", null, null, null, null);

        when(jobRepository.findById(jobId)).thenReturn(Optional.of(job));
        when(routeRepository.saveAll(any())).thenAnswer(invocation -> invocation.getArgument(0));

        Map<String, Object> geoJson = Map.of(
                "type", "FeatureCollection",
                "features", List.of(Map.of(
                        "type", "Feature",
                        "geometry", Map.of("type", "LineString",
                                "coordinates", List.of(List.of(77.23, 28.63), List.of(77.25, 28.64))),
                        "properties", Map.of(
                                "feederName", "Feeder-01",
                                "totalLengthMeters", 2500.0,
                                "total_cost", 91234.56,
                                "poleCount", 15))));

        routeService.saveRoutesFromGeoJson(jobId, geoJson);

        @SuppressWarnings("unchecked")
        ArgumentCaptor<List<GeneratedRoute>> saved = ArgumentCaptor.forClass(List.class);
        verify(routeRepository).saveAll(saved.capture());
        assertThat(saved.getValue().get(0).getTotalCost()).isEqualByComparingTo("91234.56");
    }

    /**
     * The engine's per-segment conductor cost has to reach the route row.
     *
     * <p>Conductor is the only cost component the engine attributes to a single segment, and it is
     * the largest material line in a collector network. Until this landed, every per-route figure the
     * product showed came from {@code route length × 80}.
     */
    @Test
    void saveRoutesFromGeoJson_storesThePerSegmentConductorCost() {
        UUID jobId = UUID.randomUUID();
        Project project = new Project("Test Project", "Description");
        OptimizationJob job = new OptimizationJob(project, "MULTI_OBJECTIVE_A_STAR", null, null, null, null);

        when(jobRepository.findById(jobId)).thenReturn(Optional.of(job));
        when(routeRepository.saveAll(any())).thenAnswer(invocation -> invocation.getArgument(0));

        Map<String, Object> geoJson = Map.of(
                "type", "FeatureCollection",
                "features", List.of(
                        feature("Feeder-01", "SEG-FDR001-0001"),
                        // Priced by the engine only for the first segment: the second must stay null
                        // rather than inherit a neighbour's cost or fall to zero.
                        feature("Feeder-02", "SEG-FDR002-0001")
                )
        );

        routeService.saveRoutesFromGeoJson(jobId, geoJson, Map.of(),
                Map.of("SEG-FDR001-0001", new BigDecimal("104196.89")));

        @SuppressWarnings("unchecked")
        ArgumentCaptor<List<GeneratedRoute>> saved = ArgumentCaptor.forClass(List.class);
        verify(routeRepository).saveAll(saved.capture());
        assertThat(saved.getValue()).hasSize(2);
        assertThat(saved.getValue().get(0).getConductorCost()).isEqualByComparingTo("104196.89");
        assertThat(saved.getValue().get(1).getConductorCost())
                .as("an unpriced conductor is unknown, not free")
                .isNull();
    }

    private Map<String, Object> feature(String feederName, String segmentId) {
        return Map.of(
                "type", "Feature",
                "geometry", Map.of(
                        "type", "LineString",
                        "coordinates", List.of(List.of(77.23, 28.63), List.of(77.25, 28.64))
                ),
                "properties", Map.of(
                        "feederName", feederName,
                        "segmentId", segmentId,
                        "totalLengthMeters", 2500.0,
                        "poleCount", 15
                )
        );
    }

    @Test
    void getRoutesGeoJsonForJob_success() {
        UUID projectId = UUID.randomUUID();
        UUID jobId = UUID.randomUUID();

        Project project = new Project("Test Project", "Description");
        OptimizationJob job = new OptimizationJob(project, "MULTI_OBJECTIVE_A_STAR", null, null, null, null);

        LineString lineString = geometryFactory.createLineString(new Coordinate[]{
                new Coordinate(77.23, 28.63),
                new Coordinate(77.25, 28.64)
        });

        GeneratedRoute route = new GeneratedRoute(
                job, "Feeder-01", new BigDecimal("2500.00"), new BigDecimal("150000.00"), new BigDecimal("12.5"), 15, lineString, null, null
        );

        when(projectRepository.findById(projectId)).thenReturn(Optional.of(project));
        when(jobRepository.findById(jobId)).thenReturn(Optional.of(job));
        when(routeRepository.findAllByJobIdOrderByFeederNameAsc(jobId)).thenReturn(List.of(route));
        when(poleRepository.findAllByJobIdOrderByPoleIdentifierAsc(any())).thenReturn(List.of());

        Map<String, Object> geoJson = routeService.getRoutesGeoJsonForJob(projectId, jobId);

        assertThat(geoJson).containsEntry("type", "FeatureCollection");
        assertThat(geoJson).containsKey("features");

        @SuppressWarnings("unchecked")
        List<Map<String, Object>> features = (List<Map<String, Object>>) geoJson.get("features");
        assertThat(features).hasSize(1);
        assertThat(features.get(0).get("type")).isEqualTo("Feature");
    }
}
