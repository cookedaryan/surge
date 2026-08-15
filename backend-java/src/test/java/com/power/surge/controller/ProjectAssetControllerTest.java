package com.power.surge.controller;

import com.fasterxml.jackson.databind.ObjectMapper;
import com.power.surge.dto.asset.CreateSubstationRequest;
import com.power.surge.domain.WtgStatus;
import com.power.surge.dto.asset.CreateWtgRequest;
import com.power.surge.dto.asset.GeoJsonImportResponse;
import com.power.surge.dto.asset.ProjectAssetsResponse;
import com.power.surge.dto.asset.SubstationResponse;
import com.power.surge.dto.asset.WtgResponse;
import com.power.surge.repository.ProjectRepository;
import com.power.surge.repository.SubstationRepository;
import com.power.surge.repository.WtgLocationRepository;
import com.power.surge.security.JwtTokenProvider;
import com.power.surge.service.AssetService;
import com.power.surge.service.AuthService;
import com.power.surge.service.KmzConversionResult;
import com.power.surge.service.KmzGeoJsonConverter;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.autoconfigure.data.jpa.JpaRepositoriesAutoConfiguration;
import org.springframework.boot.test.autoconfigure.web.servlet.AutoConfigureMockMvc;
import org.springframework.boot.test.autoconfigure.web.servlet.WebMvcTest;
import org.springframework.boot.test.mock.mockito.MockBean;
import org.springframework.http.MediaType;
import org.springframework.mock.web.MockMultipartFile;
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
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.multipart;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.post;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

@WebMvcTest(controllers = ProjectAssetController.class, excludeAutoConfiguration = { JpaRepositoriesAutoConfiguration.class })
@AutoConfigureMockMvc(addFilters = false)
@ActiveProfiles("test")
class ProjectAssetControllerTest {

    @Autowired
    private MockMvc mockMvc;

    @MockBean
    private JwtTokenProvider jwtTokenProvider;

    @MockBean
    private AuthService authService;

    @MockBean
    private AssetService assetService;

    @MockBean
    private KmzGeoJsonConverter kmzConverter;

    @Autowired
    private ObjectMapper objectMapper;

    @MockBean
    private ProjectRepository projectRepository;

    @MockBean
    private SubstationRepository substationRepository;

    @MockBean
    private WtgLocationRepository wtgLocationRepository;

    @Test
    void importsGeoJson() throws Exception {
        UUID projectId = UUID.randomUUID();
        UUID wtgId = UUID.randomUUID();

        WtgResponse wtg = new WtgResponse(wtgId, "WTG-001", new BigDecimal("3.000"), 77.2302, 28.6301, WtgStatus.APPROVED, true, null, Instant.now());
        GeoJsonImportResponse response = new GeoJsonImportResponse(projectId, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 1,
                Map.of("WTG", 1), List.of(wtg), List.of(), List.of(), List.of());

        when(assetService.importGeoJson(eq(projectId), any(String.class))).thenReturn(response);

        mockMvc.perform(post("/api/v1/projects/{projectId}/assets/geojson", projectId)
                        .contentType(MediaType.APPLICATION_JSON)
                        .content("""
                                {
                                  "type": "FeatureCollection",
                                  "features": [
                                    {
                                      "type": "Feature",
                                      "properties": { "assetType": "WTG", "externalId": "WTG-001" },
                                      "geometry": { "type": "Point", "coordinates": [77.2302, 28.6301] }
                                    }
                                  ]
                                }
                                """))
                .andExpect(status().isCreated())
                .andExpect(jsonPath("$.projectId").value(projectId.toString()))
                .andExpect(jsonPath("$.wtgsImported").value(1))
                .andExpect(jsonPath("$.totalImported").value(1))
                .andExpect(jsonPath("$.wtgs[0].externalId").value("WTG-001"));
    }

    @Test
    void importsKmzAssets() throws Exception {
        UUID projectId = UUID.randomUUID();
        UUID wtgId = UUID.randomUUID();

        WtgResponse wtg = new WtgResponse(wtgId, "WTG-KMZ", new BigDecimal("3.000"), 77.23, 28.63, WtgStatus.APPROVED, true, null, Instant.now());
        GeoJsonImportResponse response = new GeoJsonImportResponse(projectId, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 1,
                Map.of("WTG", 1), List.of(wtg), List.of(), List.of(), List.of());

        Map<String, Object> featureCollection = Map.of(
                "type", "FeatureCollection",
                "features", List.of(Map.of("type", "Feature"))
        );

        when(kmzConverter.convert(any())).thenReturn(
                new KmzConversionResult(featureCollection, 1, 1, 0, 0, 0, Map.of()));
        when(assetService.importGeoJson(eq(projectId), any(String.class), any(String.class))).thenReturn(response);

        MockMultipartFile file = new MockMultipartFile(
                "file",
                "test.kmz",
                "application/vnd.google-earth.kmz",
                new byte[]{0x50, 0x4B, 0x03, 0x04, 0, 0, 0, 0}
        );

        mockMvc.perform(multipart("/api/v1/projects/{projectId}/assets/kmz", projectId)
                        .file(file))
                .andExpect(status().isCreated())
                .andExpect(jsonPath("$.projectId").value(projectId.toString()))
                .andExpect(jsonPath("$.wtgsImported").value(1))
                .andExpect(jsonPath("$.wtgs[0].externalId").value("WTG-KMZ"));
    }

    @Test
    void importsKmzAssetsReturnsBadRequestOnMalformedFile() throws Exception {
        UUID projectId = UUID.randomUUID();

        when(kmzConverter.convert(any()))
                .thenThrow(new IllegalArgumentException("KMZ file contains no valid Point placemarks"));

        MockMultipartFile file = new MockMultipartFile(
                "file",
                "empty.kmz",
                "application/vnd.google-earth.kmz",
                new byte[]{1, 2, 3, 4}
        );

        mockMvc.perform(multipart("/api/v1/projects/{projectId}/assets/kmz", projectId)
                        .file(file))
                .andExpect(status().isBadRequest());
    }

    @Test
    void getsProjectAssets() throws Exception {
        UUID projectId = UUID.randomUUID();
        WtgResponse wtg = new WtgResponse(UUID.randomUUID(), "WTG-001", new BigDecimal("3.000"), 77.23, 28.63, WtgStatus.APPROVED, true, null, Instant.now());
        SubstationResponse sub = new SubstationResponse(UUID.randomUUID(), "SUB-001", new BigDecimal("100.000"), 77.25, 28.64, Instant.now());

        ProjectAssetsResponse response = new ProjectAssetsResponse(projectId, 1, 1, 1, 0, List.of(wtg), List.of(sub), List.of());
        when(assetService.getProjectAssets(projectId)).thenReturn(response);

        mockMvc.perform(get("/api/v1/projects/{projectId}/assets", projectId))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.projectId").value(projectId.toString()))
                .andExpect(jsonPath("$.totalWtgs").value(1))
                .andExpect(jsonPath("$.totalSubstations").value(1));
    }

    @Test
    void createsWtg() throws Exception {
        UUID projectId = UUID.randomUUID();
        UUID wtgId = UUID.randomUUID();
        WtgResponse response = new WtgResponse(wtgId, "WTG-001", new BigDecimal("3.500"), 77.23, 28.63, WtgStatus.APPROVED, true, null, Instant.now());

        when(assetService.createWtg(eq(projectId), any(CreateWtgRequest.class))).thenReturn(response);

        mockMvc.perform(post("/api/v1/projects/{projectId}/wtgs", projectId)
                        .contentType(MediaType.APPLICATION_JSON)
                        .content("""
                                {
                                  "externalId": "WTG-001",
                                  "capacityMw": 3.5,
                                  "longitude": 77.23,
                                  "latitude": 28.63
                                }
                                """))
                .andExpect(status().isCreated())
                .andExpect(jsonPath("$.externalId").value("WTG-001"))
                .andExpect(jsonPath("$.capacityMw").value(3.5));
    }

    @Test
    void createsSubstation() throws Exception {
        UUID projectId = UUID.randomUUID();
        UUID subId = UUID.randomUUID();
        SubstationResponse response = new SubstationResponse(subId, "SUB-001", new BigDecimal("100.000"), 77.25, 28.64, Instant.now());

        when(assetService.createSubstation(eq(projectId), any(CreateSubstationRequest.class))).thenReturn(response);

        mockMvc.perform(post("/api/v1/projects/{projectId}/substations", projectId)
                        .contentType(MediaType.APPLICATION_JSON)
                        .content("""
                                {
                                  "externalId": "SUB-001",
                                  "capacityMw": 100.0,
                                  "longitude": 77.25,
                                  "latitude": 28.64
                                }
                                """))
                .andExpect(status().isCreated())
                .andExpect(jsonPath("$.externalId").value("SUB-001"));
    }
}
