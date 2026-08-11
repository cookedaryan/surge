package com.power.surge.service;

import com.fasterxml.jackson.databind.ObjectMapper;
import com.power.surge.domain.AssetType;
import com.power.surge.domain.EvacuationTower;
import com.power.surge.domain.Project;
import com.power.surge.domain.Substation;
import com.power.surge.domain.WtgLocation;
import com.power.surge.domain.WtgStatus;
import com.power.surge.dto.asset.AssetImportPreviewResponse;
import com.power.surge.dto.asset.CommitAssetImportRequest;
import com.power.surge.dto.asset.CreateSubstationRequest;
import com.power.surge.dto.asset.CreateWtgRequest;
import com.power.surge.dto.asset.GeoJsonImportResponse;
import com.power.surge.dto.asset.ProjectAssetsResponse;
import com.power.surge.dto.asset.SubstationResponse;
import com.power.surge.dto.asset.WtgResponse;
import com.power.surge.repository.CadastralParcelRepository;
import com.power.surge.repository.EvacuationTowerRepository;
import com.power.surge.repository.ProjectRepository;
import com.power.surge.repository.ReferenceLineRepository;
import com.power.surge.repository.RestrictedAreaRepository;
import com.power.surge.repository.SubstationRepository;
import com.power.surge.repository.WtgLocationRepository;
import com.power.surge.service.classification.AssetClassifier;
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

    @Mock
    private EvacuationTowerRepository evacuationTowerRepository;

    @Mock
    private ReferenceLineRepository referenceLineRepository;

    @Mock
    private CadastralParcelRepository cadastralParcelRepository;

    @Mock
    private RestrictedAreaRepository restrictedAreaRepository;

    @Captor
    private ArgumentCaptor<List<WtgLocation>> wtgListCaptor;

    @Captor
    private ArgumentCaptor<List<Substation>> subListCaptor;

    @Captor
    private ArgumentCaptor<List<EvacuationTower>> towerListCaptor;

    private AssetService assetService;

    @BeforeEach
    void setUp() {
        assetService = new AssetService(
                projectRepository,
                wtgLocationRepository,
                substationRepository,
                evacuationTowerRepository,
                referenceLineRepository,
                cadastralParcelRepository,
                restrictedAreaRepository,
                new AssetClassifier(),
                new AssetImportStagingService(),
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

    /**
     * The defect this suite exists to prevent: a KMZ containing turbines, evacuation towers and a
     * substation used to land entirely in wtg_locations, each tower carrying a fabricated 3 MW
     * capacity and feeding the optimiser.
     */
    @Test
    void splitsKmzFeaturesAcrossTurbinesTowersAndSubstations() {
        UUID projectId = UUID.randomUUID();
        Project project = new Project("Uravakonda", "PCN route");
        when(projectRepository.findById(projectId)).thenReturn(Optional.of(project));
        when(wtgLocationRepository.saveAll(any())).thenAnswer(inv -> inv.getArgument(0));
        when(substationRepository.saveAll(any())).thenAnswer(inv -> inv.getArgument(0));
        when(evacuationTowerRepository.saveAll(any())).thenAnswer(inv -> inv.getArgument(0));

        String geoJson = """
                {
                  "type": "FeatureCollection",
                  "features": [
                    { "type": "Feature",
                      "properties": { "externalId": "KS67_S1", "kmlFolderPath": "Uravakonda / Approved" },
                      "geometry": { "type": "Point", "coordinates": [77.10, 14.30] } },
                    { "type": "Feature",
                      "properties": { "externalId": "KS82_S2", "kmlFolderPath": "Uravakonda / Cancel Location" },
                      "geometry": { "type": "Point", "coordinates": [77.11, 14.31] } },
                    { "type": "Feature",
                      "properties": { "externalId": "20/12", "kmlFolderPath": "Uravakonda / HT Lines / Gantry - AP34 / Sheet1" },
                      "geometry": { "type": "Point", "coordinates": [77.12, 14.32] } },
                    { "type": "Feature",
                      "properties": { "externalId": "GANTRY", "kmlFolderPath": "Uravakonda / HT Lines / Gantry - AP34 / Sheet1" },
                      "geometry": { "type": "Point", "coordinates": [77.13, 14.33] } },
                    { "type": "Feature",
                      "properties": { "externalId": "Mopidi PSS", "kmlFolderPath": "Uravakonda / HT Lines / PSS Land" },
                      "geometry": { "type": "Point", "coordinates": [77.14, 14.34] } },
                    { "type": "Feature",
                      "properties": { "externalId": "BH-1", "kmlFolderPath": "Uravakonda / Anantapur PSS_Borehole.kmz" },
                      "geometry": { "type": "Point", "coordinates": [77.15, 14.35] } }
                  ]
                }
                """;

        GeoJsonImportResponse response = assetService.importGeoJson(projectId, geoJson);

        assertThat(response.wtgsImported()).isEqualTo(2);
        assertThat(response.towersImported()).isEqualTo(2);
        assertThat(response.substationsImported()).isEqualTo(1);
        assertThat(response.surveyPointsSkipped()).isEqualTo(1);

        verify(wtgLocationRepository).saveAll(wtgListCaptor.capture());
        verify(evacuationTowerRepository).saveAll(towerListCaptor.capture());

        assertThat(wtgListCaptor.getValue())
                .extracting(WtgLocation::getExternalId)
                .containsExactly("KS67_S1", "KS82_S2");

        assertThat(towerListCaptor.getValue())
                .extracting(EvacuationTower::getExternalId)
                .containsExactly("20/12", "GANTRY");

        // Towers carry structural metadata rather than a fabricated generation capacity.
        assertThat(towerListCaptor.getValue().get(0).getTowerType()).isEqualTo("SUSPENSION");
        assertThat(towerListCaptor.getValue().get(0).getLineSection()).isEqualTo("20");
        assertThat(towerListCaptor.getValue().get(1).getTowerType()).isEqualTo("GANTRY");
    }

    @Test
    void derivesTurbineStatusFromSourceFolderAndExcludesCancelledFromOptimisation() {
        UUID projectId = UUID.randomUUID();
        Project project = new Project("Uravakonda", null);
        when(projectRepository.findById(projectId)).thenReturn(Optional.of(project));
        when(wtgLocationRepository.saveAll(any())).thenAnswer(inv -> inv.getArgument(0));
        when(substationRepository.saveAll(any())).thenAnswer(inv -> inv.getArgument(0));
        when(evacuationTowerRepository.saveAll(any())).thenAnswer(inv -> inv.getArgument(0));

        String geoJson = """
                {
                  "type": "FeatureCollection",
                  "features": [
                    { "type": "Feature",
                      "properties": { "externalId": "KS67_S1", "kmlFolderPath": "Site / Approved" },
                      "geometry": { "type": "Point", "coordinates": [77.10, 14.30] } },
                    { "type": "Feature",
                      "properties": { "externalId": "KS82_S2", "kmlFolderPath": "Site / Cancel Location" },
                      "geometry": { "type": "Point", "coordinates": [77.11, 14.31] } }
                  ]
                }
                """;

        assetService.importGeoJson(projectId, geoJson);
        verify(wtgLocationRepository).saveAll(wtgListCaptor.capture());

        assertThat(wtgListCaptor.getValue())
                .extracting(WtgLocation::getExternalId, WtgLocation::getStatus)
                .containsExactly(
                        org.assertj.core.api.Assertions.tuple("KS67_S1", WtgStatus.APPROVED),
                        org.assertj.core.api.Assertions.tuple("KS82_S2", WtgStatus.CANCELLED));

        assertThat(wtgListCaptor.getValue().get(0).getStatus().isOptimisable()).isTrue();
        assertThat(wtgListCaptor.getValue().get(1).getStatus().isOptimisable()).isFalse();
    }

    @Test
    void rejectsUnclassifiableFeaturesInsteadOfDefaultingThemToTurbines() {
        UUID projectId = UUID.randomUUID();
        Project project = new Project("Uravakonda", null);
        when(projectRepository.findById(projectId)).thenReturn(Optional.of(project));

        String geoJson = """
                {
                  "type": "FeatureCollection",
                  "features": [
                    { "type": "Feature",
                      "properties": { "externalId": "Feeder 4", "kmlFolderPath": "Site / G.O.Boundary" },
                      "geometry": { "type": "Point", "coordinates": [77.10, 14.30] } }
                  ]
                }
                """;

        assertThatThrownBy(() -> assetService.importGeoJson(projectId, geoJson))
                .isInstanceOf(IllegalArgumentException.class)
                .hasMessageContaining("Could not classify")
                .hasMessageContaining("Feeder 4");
    }

    @Test
    void previewClassifiesWithoutPersistingAndCommitAppliesOverrides() {
        UUID projectId = UUID.randomUUID();
        Project project = new Project("Uravakonda", null);
        when(projectRepository.findById(projectId)).thenReturn(Optional.of(project));

        Map<String, Object> featureCollection = Map.of(
                "type", "FeatureCollection",
                "features", List.of(Map.of(
                        "type", "Feature",
                        "properties", Map.of("externalId", "KS67_S1", "kmlFolderPath", "Site / Approved"),
                        "geometry", Map.of("type", "Point", "coordinates", List.of(77.10, 14.30)))));

        AssetImportPreviewResponse preview =
                assetService.previewImport(projectId, "route.kmz", featureCollection, 12, Map.of("LineString", 4));

        assertThat(preview.countsByType()).containsEntry(AssetType.WTG.name(), 1);
        assertThat(preview.duplicatesRemoved()).isEqualTo(12);
        assertThat(preview.features()).singleElement()
                .satisfies(f -> assertThat(f.classifiedAs()).isEqualTo(AssetType.WTG));
        verify(wtgLocationRepository, org.mockito.Mockito.never()).saveAll(any());

        // The user disagrees with the detection and reclassifies it as a tower before committing.
        when(wtgLocationRepository.saveAll(any())).thenAnswer(inv -> inv.getArgument(0));
        when(substationRepository.saveAll(any())).thenAnswer(inv -> inv.getArgument(0));
        when(evacuationTowerRepository.saveAll(any())).thenAnswer(inv -> inv.getArgument(0));

        GeoJsonImportResponse committed = assetService.commitImport(projectId, new CommitAssetImportRequest(
                preview.importId(), Map.of("KS67_S1", "EVACUATION_TOWER"), Map.of(), null, true));

        assertThat(committed.towersImported()).isEqualTo(1);
        assertThat(committed.wtgsImported()).isZero();
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
