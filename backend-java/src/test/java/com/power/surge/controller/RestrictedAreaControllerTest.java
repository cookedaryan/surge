package com.power.surge.controller;

import com.power.surge.dto.restriction.RestrictedAreaResponse;
import com.power.surge.repository.ProjectRepository;
import com.power.surge.repository.RestrictedAreaRepository;
import com.power.surge.service.RestrictedAreaService;
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

@WebMvcTest(controllers = RestrictedAreaController.class, excludeAutoConfiguration = { JpaRepositoriesAutoConfiguration.class })
@AutoConfigureMockMvc(addFilters = false)
@ActiveProfiles("test")
class RestrictedAreaControllerTest {

    @Autowired
    private MockMvc mockMvc;

    @MockBean
    private JwtTokenProvider jwtTokenProvider;

    @MockBean
    private com.power.surge.service.AuthService authService;

    @MockBean
    private RestrictedAreaService restrictedAreaService;

    @MockBean
    private ProjectRepository projectRepository;

    @MockBean
    private RestrictedAreaRepository restrictedAreaRepository;

    @Test
    void importsRestrictedAreasGeoJson() throws Exception {
        UUID projectId = UUID.randomUUID();
        UUID areaId = UUID.randomUUID();

        RestrictedAreaResponse response = new RestrictedAreaResponse(
                areaId,
                projectId,
                "National Park Buffer",
                "ENVIRONMENTAL",
                new BigDecimal("500.00"),
                List.of(List.of(List.of(77.20, 28.60), List.of(77.21, 28.60), List.of(77.21, 28.61), List.of(77.20, 28.60))),
                Instant.now()
        );

        when(restrictedAreaService.importRestrictedAreasGeoJson(eq(projectId), any())).thenReturn(List.of(response));

        mockMvc.perform(post("/api/v1/projects/{projectId}/restricted-areas/geojson", projectId)
                        .contentType(MediaType.APPLICATION_JSON)
                        .content("""
                                {
                                  "type": "FeatureCollection",
                                  "features": [
                                    {
                                      "type": "Feature",
                                      "properties": { "name": "National Park Buffer", "restrictionType": "ENVIRONMENTAL", "bufferMeters": 500.0 },
                                      "geometry": {
                                        "type": "Polygon",
                                        "coordinates": [[[77.20, 28.60], [77.21, 28.60], [77.21, 28.61], [77.20, 28.60]]]
                                      }
                                    }
                                  ]
                                }
                                """))
                .andExpect(status().isCreated())
                .andExpect(jsonPath("$[0].name").value("National Park Buffer"))
                .andExpect(jsonPath("$[0].restrictionType").value("ENVIRONMENTAL"));
    }

    @Test
    void getsRestrictedAreasGeoJson() throws Exception {
        UUID projectId = UUID.randomUUID();

        Map<String, Object> geoJson = Map.of(
                "type", "FeatureCollection",
                "features", List.of(
                        Map.of(
                                "type", "Feature",
                                "properties", Map.of("name", "River Exclusion", "restrictionType", "WATER_BODY")
                        )
                )
        );

        when(restrictedAreaService.getRestrictedAreasGeoJson(projectId)).thenReturn(geoJson);

        mockMvc.perform(get("/api/v1/projects/{projectId}/restricted-areas/geojson", projectId))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.type").value("FeatureCollection"))
                .andExpect(jsonPath("$.features[0].properties.name").value("River Exclusion"));
    }
}
