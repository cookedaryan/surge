package com.power.surge.service;

import com.fasterxml.jackson.databind.ObjectMapper;
import com.power.surge.domain.Project;
import com.power.surge.domain.RestrictedArea;
import com.power.surge.dto.restriction.CreateRestrictedAreaRequest;
import com.power.surge.dto.restriction.RestrictedAreaResponse;
import com.power.surge.repository.ProjectRepository;
import com.power.surge.repository.RestrictedAreaRepository;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.Mock;
import org.mockito.junit.jupiter.MockitoExtension;

import java.math.BigDecimal;
import java.util.List;
import java.util.Optional;
import java.util.UUID;

import static org.assertj.core.api.Assertions.assertThat;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.Mockito.when;

@ExtendWith(MockitoExtension.class)
class RestrictedAreaServiceTest {

    @Mock
    private ProjectRepository projectRepository;

    @Mock
    private RestrictedAreaRepository restrictedAreaRepository;

    private RestrictedAreaService restrictedAreaService;

    @BeforeEach
    void setUp() {
        restrictedAreaService = new RestrictedAreaService(projectRepository, restrictedAreaRepository, new ObjectMapper());
    }

    @Test
    void createRestrictedArea_success() {
        UUID projectId = UUID.randomUUID();
        Project project = new Project("Test Project", "Description");

        when(projectRepository.findById(projectId)).thenReturn(Optional.of(project));
        when(restrictedAreaRepository.save(any(RestrictedArea.class))).thenAnswer(invocation -> invocation.getArgument(0));

        CreateRestrictedAreaRequest request = new CreateRestrictedAreaRequest(
                "Forest Reserve Buffer",
                "ENVIRONMENTAL",
                new BigDecimal("250.00"),
                List.of(List.of(List.of(77.20, 28.60), List.of(77.21, 28.60), List.of(77.21, 28.61), List.of(77.20, 28.60)))
        );

        RestrictedAreaResponse response = restrictedAreaService.createRestrictedArea(projectId, request);

        assertThat(response).isNotNull();
        assertThat(response.name()).isEqualTo("Forest Reserve Buffer");
        assertThat(response.restrictionType()).isEqualTo("ENVIRONMENTAL");
        assertThat(response.bufferMeters()).isEqualByComparingTo("250.00");
    }

    @Test
    void importRestrictedAreasGeoJson_success() {
        UUID projectId = UUID.randomUUID();
        Project project = new Project("Test Project", "Description");

        when(projectRepository.findById(projectId)).thenReturn(Optional.of(project));
        when(restrictedAreaRepository.findAllByProjectIdOrderByNameAsc(projectId)).thenReturn(List.of());
        when(restrictedAreaRepository.saveAll(any())).thenAnswer(invocation -> invocation.getArgument(0));

        String geoJson = """
                {
                  "type": "FeatureCollection",
                  "features": [
                    {
                      "type": "Feature",
                      "properties": { "name": "River Buffer", "restrictionType": "WATER_BODY", "bufferMeters": 100.0 },
                      "geometry": {
                        "type": "Polygon",
                        "coordinates": [[[77.20, 28.60], [77.21, 28.60], [77.21, 28.61], [77.20, 28.60]]]
                      }
                    }
                  ]
                }
                """;

        List<RestrictedAreaResponse> responses = restrictedAreaService.importRestrictedAreasGeoJson(projectId, geoJson);

        assertThat(responses).hasSize(1);
        assertThat(responses.get(0).name()).isEqualTo("River Buffer");
        assertThat(responses.get(0).restrictionType()).isEqualTo("WATER_BODY");
    }
}
