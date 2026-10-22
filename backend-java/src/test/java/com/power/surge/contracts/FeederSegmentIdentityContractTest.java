package com.power.surge.contracts;

import com.fasterxml.jackson.core.type.TypeReference;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.power.surge.domain.GeneratedRoute;
import com.power.surge.domain.OptimizationJob;
import com.power.surge.domain.Project;
import com.power.surge.repository.GeneratedPoleRepository;
import com.power.surge.repository.GeneratedRouteRepository;
import com.power.surge.repository.OptimizationJobRepository;
import com.power.surge.repository.ProjectRepository;
import com.power.surge.service.CableCatalogueService;
import com.power.surge.service.RouteService;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.ArgumentCaptor;
import org.mockito.Mock;
import org.mockito.junit.jupiter.MockitoExtension;

import java.io.IOException;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.Optional;
import java.util.UUID;

import static org.assertj.core.api.Assertions.assertThat;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.when;

/**
 * Stage 0 contract C11 (WP0A-3): one V1 route Feature is one routed segment under one feeder.
 *
 * <p>Reads the shared fixture in {@code contracts/fixtures/} so Python and Java are held to the same
 * document. TRD §6.3 recorded a feeder-identity mismatch; this proves current persistence keeps the
 * engine's feeder name and segment id per row, which is what BOM and export aggregate on.
 */
@ExtendWith(MockitoExtension.class)
class FeederSegmentIdentityContractTest {

    private static final Path FIXTURE =
            Path.of("..", "contracts", "fixtures", "feeder-segment-identity.json");

    @Mock
    private ProjectRepository projectRepository;

    @Mock
    private OptimizationJobRepository jobRepository;

    @Mock
    private GeneratedRouteRepository routeRepository;

    @Mock
    private GeneratedPoleRepository poleRepository;

    @Mock
    private CableCatalogueService cableCatalogueService;

    @Test
    @SuppressWarnings("unchecked")
    void eachSegmentFeatureIsPersistedAsOneRowUnderTheEnginesFeeder() throws IOException {
        Map<String, Object> fixture = new ObjectMapper()
                .readValue(Files.readString(FIXTURE), new TypeReference<>() {});
        RouteService routeService = new RouteService(
                projectRepository, jobRepository, routeRepository, poleRepository,
                new ObjectMapper(), cableCatalogueService);

        UUID jobId = UUID.randomUUID();
        OptimizationJob job = new OptimizationJob(
                new Project("Contract", "C11"), "MULTI_OBJECTIVE_A_STAR", null, null, null, null);
        when(jobRepository.findById(jobId)).thenReturn(Optional.of(job));
        when(routeRepository.saveAll(any())).thenAnswer(invocation -> invocation.getArgument(0));

        routeService.saveRoutesFromGeoJson(
                jobId, (Map<String, Object>) fixture.get("feeder_routes_geojson"));

        ArgumentCaptor<List<GeneratedRoute>> saved = ArgumentCaptor.forClass(List.class);
        verify(routeRepository).saveAll(saved.capture());

        List<Map<String, String>> rows = saved.getValue().stream()
                .map(route -> Map.of("feederName", route.getFeederName(), "segmentId", route.getSegmentId()))
                .toList();
        assertThat(rows).isEqualTo(fixture.get("expected_route_rows"));

        Map<String, Integer> countByFeeder = new LinkedHashMap<>();
        for (GeneratedRoute route : saved.getValue()) {
            countByFeeder.merge(route.getFeederName(), 1, Integer::sum);
        }
        assertThat(countByFeeder).isEqualTo(fixture.get("expected_bom_segment_count_by_feeder"));
    }
}
