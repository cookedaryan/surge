package com.power.surge.service;

import com.fasterxml.jackson.databind.ObjectMapper;
import com.power.surge.domain.CadastralParcel;
import com.power.surge.domain.Project;
import com.power.surge.dto.parcel.CreateParcelRequest;
import com.power.surge.dto.parcel.ParcelResponse;
import com.power.surge.repository.CadastralParcelRepository;
import com.power.surge.repository.ProjectRepository;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.Mock;
import org.mockito.junit.jupiter.MockitoExtension;

import java.math.BigDecimal;
import java.util.List;
import java.util.Map;
import java.util.Optional;
import java.util.UUID;

import static org.assertj.core.api.Assertions.assertThat;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.Mockito.when;

@ExtendWith(MockitoExtension.class)
class ParcelServiceTest {

    @Mock
    private ProjectRepository projectRepository;

    @Mock
    private CadastralParcelRepository parcelRepository;

    private ParcelService parcelService;

    @BeforeEach
    void setUp() {
        parcelService = new ParcelService(projectRepository, parcelRepository, new ObjectMapper());
    }

    @Test
    void createParcel_success() {
        UUID projectId = UUID.randomUUID();
        Project project = new Project("Test Project", "Description");

        when(projectRepository.findById(projectId)).thenReturn(Optional.of(project));
        when(parcelRepository.save(any(CadastralParcel.class))).thenAnswer(invocation -> invocation.getArgument(0));

        CreateParcelRequest request = new CreateParcelRequest(
                "P-001",
                "Jane Doe",
                null, // ownerId
                "AVAILABLE", // availabilityStatus
                "PURCHASE", // transactionMode
                "ESTIMATED", // priceStatus
                null, // priceDate
                new BigDecimal("120.50"),
                List.of(List.of(List.of(77.20, 28.60), List.of(77.21, 28.60), List.of(77.21, 28.61), List.of(77.20, 28.60)))
        );

        ParcelResponse response = parcelService.createParcel(projectId, request);

        assertThat(response).isNotNull();
        assertThat(response.parcelId()).isEqualTo("P-001");
        assertThat(response.ownerName()).isEqualTo("Jane Doe");
        assertThat(response.acquisitionCostPerM2()).isEqualByComparingTo("120.50");
    }

    @Test
    void importParcelsGeoJson_success() {
        UUID projectId = UUID.randomUUID();
        Project project = new Project("Test Project", "Description");

        when(projectRepository.findById(projectId)).thenReturn(Optional.of(project));
        when(parcelRepository.findAllByProjectIdOrderByParcelIdAsc(projectId)).thenReturn(List.of());
        when(parcelRepository.saveAll(any())).thenAnswer(invocation -> invocation.getArgument(0));

        String geoJson = """
                {
                  "type": "FeatureCollection",
                  "features": [
                    {
                      "type": "Feature",
                      "properties": { "parcelId": "P-001", "ownerName": "Jane Doe", "acquisitionCostPerM2": 120.5 },
                      "geometry": {
                        "type": "Polygon",
                        "coordinates": [[[77.20, 28.60], [77.21, 28.60], [77.21, 28.61], [77.20, 28.60]]]
                      }
                    }
                  ]
                }
                """;

        List<ParcelResponse> responses = parcelService.importParcelsGeoJson(projectId, geoJson);

        assertThat(responses).hasSize(1);
        assertThat(responses.get(0).parcelId()).isEqualTo("P-001");
    }
}
