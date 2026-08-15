package com.power.surge.controller;

import com.power.surge.dto.parcel.ParcelResponse;
import com.power.surge.repository.CadastralParcelRepository;
import com.power.surge.repository.ProjectRepository;
import com.power.surge.service.ParcelService;
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

@WebMvcTest(controllers = CadastralParcelController.class, excludeAutoConfiguration = { JpaRepositoriesAutoConfiguration.class })
@AutoConfigureMockMvc(addFilters = false)
@ActiveProfiles("test")
class CadastralParcelControllerTest {

    @Autowired
    private MockMvc mockMvc;

    @MockBean
    private JwtTokenProvider jwtTokenProvider;

    // The authentication filter now resolves the account behind the token, so every slice that
    // builds the security chain needs the repository it reads.
    @MockBean
    private com.power.surge.repository.UserRepository userRepository;

    @MockBean
    private com.power.surge.service.AuthService authService;

    @MockBean
    private ParcelService parcelService;

    @MockBean
    private ProjectRepository projectRepository;

    @MockBean
    private CadastralParcelRepository parcelRepository;

    @Test
    void importsParcelsGeoJson() throws Exception {
        UUID projectId = UUID.randomUUID();
        UUID parcelUuid = UUID.randomUUID();

        ParcelResponse response = new ParcelResponse(
                parcelUuid,
                projectId,
                "P-0001",
                "John Doe",
                new BigDecimal("150.00"),
                List.of(List.of(List.of(77.20, 28.60), List.of(77.21, 28.60), List.of(77.21, 28.61), List.of(77.20, 28.60))),
                Instant.now()
        );

        when(parcelService.importParcelsGeoJson(eq(projectId), any())).thenReturn(List.of(response));

        mockMvc.perform(post("/api/v1/projects/{projectId}/parcels/geojson", projectId)
                        .contentType(MediaType.APPLICATION_JSON)
                        .content("""
                                {
                                  "type": "FeatureCollection",
                                  "features": [
                                    {
                                      "type": "Feature",
                                      "properties": { "parcelId": "P-0001", "ownerName": "John Doe", "acquisitionCostPerM2": 150.0 },
                                      "geometry": {
                                        "type": "Polygon",
                                        "coordinates": [[[77.20, 28.60], [77.21, 28.60], [77.21, 28.61], [77.20, 28.60]]]
                                      }
                                    }
                                  ]
                                }
                                """))
                .andExpect(status().isCreated())
                .andExpect(jsonPath("$[0].parcelId").value("P-0001"))
                .andExpect(jsonPath("$[0].ownerName").value("John Doe"));
    }

    @Test
    void getsParcelsGeoJson() throws Exception {
        UUID projectId = UUID.randomUUID();

        Map<String, Object> geoJson = Map.of(
                "type", "FeatureCollection",
                "features", List.of(
                        Map.of(
                                "type", "Feature",
                                "properties", Map.of("parcelId", "P-0001", "ownerName", "John Doe")
                        )
                )
        );

        when(parcelService.getParcelsGeoJson(projectId)).thenReturn(geoJson);

        mockMvc.perform(get("/api/v1/projects/{projectId}/parcels/geojson", projectId))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.type").value("FeatureCollection"))
                .andExpect(jsonPath("$.features[0].properties.parcelId").value("P-0001"));
    }
}
