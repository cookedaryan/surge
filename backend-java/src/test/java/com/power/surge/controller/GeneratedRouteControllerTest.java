package com.power.surge.controller;

import com.power.surge.dto.route.CreateRouteRequest;
import com.power.surge.dto.route.GeneratedRouteResponse;
import com.power.surge.repository.GeneratedRouteRepository;
import com.power.surge.repository.OptimizationJobRepository;
import com.power.surge.repository.ProjectRepository;
import com.power.surge.service.RouteService;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.autoconfigure.data.jpa.JpaRepositoriesAutoConfiguration;
import org.springframework.boot.test.autoconfigure.web.servlet.WebMvcTest;
import org.springframework.boot.test.mock.mockito.MockBean;
import org.springframework.http.MediaType;
import org.springframework.test.context.ActiveProfiles;
import org.springframework.test.web.servlet.MockMvc;

import java.math.BigDecimal;
import java.time.Instant;
import java.util.List;
import java.util.Map;
import java.util.UUID;

import static org.mockito.ArgumentMatchers.any;
import static org.mockito.ArgumentMatchers.eq;
import static org.mockito.Mockito.when;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.post;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

import org.springframework.boot.test.autoconfigure.web.servlet.AutoConfigureMockMvc;
import com.power.surge.security.JwtTokenProvider;

@WebMvcTest(controllers = GeneratedRouteController.class, excludeAutoConfiguration = { JpaRepositoriesAutoConfiguration.class })
@AutoConfigureMockMvc(addFilters = false)
@ActiveProfiles("test")
class GeneratedRouteControllerTest {

    @Autowired
    private MockMvc mockMvc;

    @MockBean
    private JwtTokenProvider jwtTokenProvider;

    @MockBean
    private RouteService routeService;

    @MockBean
    private ProjectRepository projectRepository;

    @MockBean
    private OptimizationJobRepository jobRepository;

    @MockBean
    private GeneratedRouteRepository routeRepository;

    @Test
    void createsRoutes() throws Exception {
        UUID projectId = UUID.randomUUID();
        UUID jobId = UUID.randomUUID();
        UUID routeId = UUID.randomUUID();

        GeneratedRouteResponse response = new GeneratedRouteResponse(
                routeId,
                jobId,
                "Feeder-01",
                new BigDecimal("2500.00"),
                new BigDecimal("150000.00"),
                new BigDecimal("12.50"),
                15,
                List.of(List.of(77.23, 28.63), List.of(77.25, 28.64)),
                null,
                Instant.now()
        );

        when(routeService.saveRoutes(eq(jobId), any())).thenReturn(List.of(response));

        mockMvc.perform(post("/api/v1/projects/{projectId}/jobs/{jobId}/routes", projectId, jobId)
                        .contentType(MediaType.APPLICATION_JSON)
                        .content("""
                                [
                                  {
                                    "feederName": "Feeder-01",
                                    "totalLengthMeters": 2500.0,
                                    "totalCost": 150000.0,
                                    "electricalLossesKw": 12.5,
                                    "poleCount": 15,
                                    "coordinates": [[77.23, 28.63], [77.25, 28.64]]
                                  }
                                ]
                                """))
                .andExpect(status().isCreated())
                .andExpect(jsonPath("$[0].id").value(routeId.toString()))
                .andExpect(jsonPath("$[0].feederName").value("Feeder-01"))
                .andExpect(jsonPath("$[0].poleCount").value(15));
    }

    @Test
    void getsRoutesForJob() throws Exception {
        UUID projectId = UUID.randomUUID();
        UUID jobId = UUID.randomUUID();
        UUID routeId = UUID.randomUUID();

        GeneratedRouteResponse response = new GeneratedRouteResponse(
                routeId,
                jobId,
                "Feeder-01",
                new BigDecimal("2500.00"),
                new BigDecimal("150000.00"),
                new BigDecimal("12.50"),
                15,
                List.of(List.of(77.23, 28.63), List.of(77.25, 28.64)),
                null,
                Instant.now()
        );

        when(routeService.getRoutesForJob(projectId, jobId)).thenReturn(List.of(response));

        mockMvc.perform(get("/api/v1/projects/{projectId}/jobs/{jobId}/routes", projectId, jobId))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$[0].id").value(routeId.toString()))
                .andExpect(jsonPath("$[0].feederName").value("Feeder-01"));
    }

    @Test
    void getsRoutesGeoJsonForJob() throws Exception {
        UUID projectId = UUID.randomUUID();
        UUID jobId = UUID.randomUUID();

        Map<String, Object> geoJson = Map.of(
                "type", "FeatureCollection",
                "features", List.of(
                        Map.of(
                                "type", "Feature",
                                "id", UUID.randomUUID().toString(),
                                "geometry", Map.of(
                                        "type", "LineString",
                                        "coordinates", List.of(List.of(77.23, 28.63), List.of(77.25, 28.64))
                                ),
                                "properties", Map.of("feederName", "Feeder-01")
                        )
                )
        );

        when(routeService.getRoutesGeoJsonForJob(projectId, jobId)).thenReturn(geoJson);

        mockMvc.perform(get("/api/v1/projects/{projectId}/jobs/{jobId}/routes/geojson", projectId, jobId))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.type").value("FeatureCollection"))
                .andExpect(jsonPath("$.features[0].properties.feederName").value("Feeder-01"));
    }
}
