package com.power.surge.service;

import com.fasterxml.jackson.databind.ObjectMapper;
import com.power.surge.domain.Project;
import com.power.surge.domain.Substation;
import com.power.surge.domain.WtgLocation;
import com.power.surge.dto.asset.CreateSubstationRequest;
import com.power.surge.dto.asset.CreateWtgRequest;
import com.power.surge.dto.asset.GeoJsonImportResponse;
import com.power.surge.dto.asset.ProjectAssetsResponse;
import com.power.surge.dto.asset.SubstationResponse;
import com.power.surge.dto.asset.WtgResponse;
import com.power.surge.repository.ProjectRepository;
import com.power.surge.repository.SubstationRepository;
import com.power.surge.repository.WtgLocationRepository;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.ArgumentCaptor;
import org.mockito.Captor;
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
class AssetServiceTest {

    @Mock
    private ProjectRepository projectRepository;

    @Mock
    private WtgLocationRepository wtgLocationRepository;

    @Mock
    private SubstationRepository substationRepository;

    @Captor
    private ArgumentCaptor<List<WtgLocation>> wtgListCaptor;

    @Captor
    private ArgumentCaptor<List<Substation>> subListCaptor;

    private AssetService assetService;

    @BeforeEach
    void setUp() {
        assetService = new AssetService(
                projectRepository,
                wtgLocationRepository,
                substationRepository,
                new ObjectMapper()
        );
    }

    @Test
    void importsValidGeoJsonFeatureCollection() {
        UUID projectId = UUID.randomUUID();
        Project project = new Project("North Ridge", "Wind farm");
        when(projectRepository.findById(projectId)).thenReturn(Optional.of(project));
        when(wtgLocationRepository.saveAll(any())).thenAnswer(inv -> inv.getArgument(0));
        when(substationRepository.saveAll(any())).thenAnswer(inv -> inv.getArgument(0));

        String geoJson = """
                {
                  "type": "FeatureCollection",
                  "features": [
                    {
                      "type": "Feature",
                      "properties": {
                        "assetType": "WTG",
                        "externalId": "WTG-001",
                        "capacityMw": 3.5
                      },
                      "geometry": {
                        "type": "Point",
                        "coordinates": [77.2302, 28.6301]
                      }
                    },
                    {
                      "type": "Feature",
                      "properties": {
                        "assetType": "SUBSTATION",
                        "externalId": "SUB-001",
                        "capacityMw": 100.0
                      },
                      "geometry": {
                        "type": "Point",
                        "coordinates": [77.2500, 28.6400]
                      }
                    }
                  ]
                }
                """;

        GeoJsonImportResponse response = assetService.importGeoJson(projectId, geoJson);

        verify(wtgLocationRepository).saveAll(wtgListCaptor.capture());
        verify(substationRepository).saveAll(subListCaptor.capture());

        assertThat(response.wtgsImported()).isEqualTo(1);
        assertThat(response.substationsImported()).isEqualTo(1);
        assertThat(response.totalImported()).isEqualTo(2);

        WtgLocation savedWtg = wtgListCaptor.getValue().get(0);
        assertThat(savedWtg.getExternalId()).isEqualTo("WTG-001");
        assertThat(savedWtg.getCapacityMw()).isEqualTo("3.5");
        assertThat(savedWtg.getLocation().getX()).isEqualTo(77.2302);
        assertThat(savedWtg.getLocation().getY()).isEqualTo(28.6301);

        Substation savedSub = subListCaptor.getValue().get(0);
        assertThat(savedSub.getExternalId()).isEqualTo("SUB-001");
        assertThat(savedSub.getCapacityMw()).isEqualTo("100.0");
    }

    @Test
    void rejectsInvalidCoordinatesInGeoJson() {
        UUID projectId = UUID.randomUUID();
        Project project = new Project("North Ridge", null);
        when(projectRepository.findById(projectId)).thenReturn(Optional.of(project));

        String invalidGeoJson = """
                {
                  "type": "FeatureCollection",
                  "features": [
                    {
                      "type": "Feature",
                      "properties": { "externalId": "WTG-999" },
                      "geometry": {
                        "type": "Point",
                        "coordinates": [200.0, 28.6301]
                      }
                    }
                  ]
                }
                """;

        assertThatThrownBy(() -> assetService.importGeoJson(projectId, invalidGeoJson))
                .isInstanceOf(IllegalArgumentException.class)
                .hasMessageContaining("Longitude must be between -180 and 180 degrees");
    }

    @Test
    void createsWtgFromRequest() {
        UUID projectId = UUID.randomUUID();
        Project project = new Project("North Ridge", null);
        when(projectRepository.findById(projectId)).thenReturn(Optional.of(project));
        when(wtgLocationRepository.save(any(WtgLocation.class))).thenAnswer(inv -> inv.getArgument(0));

        CreateWtgRequest request = new CreateWtgRequest("WTG-101", new BigDecimal("4.200"), 77.1000, 28.5000);
        WtgResponse response = assetService.createWtg(projectId, request);

        assertThat(response.externalId()).isEqualTo("WTG-101");
        assertThat(response.capacityMw()).isEqualTo(new BigDecimal("4.200"));
        assertThat(response.longitude()).isEqualTo(77.1000);
        assertThat(response.latitude()).isEqualTo(28.5000);
    }

    @Test
    void exportsProjectAssetsAsGeoJson() {
        UUID projectId = UUID.randomUUID();
        Project project = new Project("North Ridge", null);
        when(projectRepository.findById(projectId)).thenReturn(Optional.of(project));

        Map<String, Object> geoJsonMap = assetService.getProjectAssetsGeoJson(projectId);

        assertThat(geoJsonMap.get("type")).isEqualTo("FeatureCollection");
        assertThat(geoJsonMap).containsKey("features");
    }
}
