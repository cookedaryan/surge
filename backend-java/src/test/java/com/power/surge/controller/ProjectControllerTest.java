package com.power.surge.controller;

import com.power.surge.dto.project.CreateProjectRequest;
import com.power.surge.dto.project.ProjectResponse;
import com.power.surge.repository.ProjectRepository;
import com.power.surge.repository.SubstationRepository;
import com.power.surge.repository.WtgLocationRepository;
import com.power.surge.service.ProjectNotFoundException;
import com.power.surge.service.ProjectService;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.autoconfigure.web.servlet.WebMvcTest;
import org.springframework.boot.test.mock.mockito.MockBean;
import org.springframework.http.MediaType;
import org.springframework.boot.autoconfigure.data.jpa.JpaRepositoriesAutoConfiguration;
import org.springframework.test.context.ActiveProfiles;
import org.springframework.test.web.servlet.MockMvc;

import java.time.Instant;
import java.util.UUID;

import static org.hamcrest.Matchers.endsWith;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.Mockito.when;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.post;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.header;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

import org.springframework.boot.test.autoconfigure.web.servlet.AutoConfigureMockMvc;
import com.power.surge.security.JwtTokenProvider;

@WebMvcTest(controllers = ProjectController.class, excludeAutoConfiguration = { JpaRepositoriesAutoConfiguration.class })
@AutoConfigureMockMvc(addFilters = false)
@ActiveProfiles("test")
class ProjectControllerTest {

    @Autowired
    private MockMvc mockMvc;

    @MockBean
    private JwtTokenProvider jwtTokenProvider;

    @MockBean
    private ProjectService projectService;

    @MockBean
    private ProjectRepository projectRepository;

    @MockBean
    private SubstationRepository substationRepository;

    @MockBean
    private WtgLocationRepository wtgLocationRepository;

    @Test
    void createsProject() throws Exception {
        UUID projectId = UUID.randomUUID();
        ProjectResponse project = new ProjectResponse(
                projectId,
                "North Ridge",
                "Wind farm project",
                "EPSG:4326",
                Instant.parse("2026-08-08T00:00:00Z"),
                Instant.parse("2026-08-08T00:00:00Z")
        );
        when(projectService.createProject(any(CreateProjectRequest.class))).thenReturn(project);

        mockMvc.perform(post("/api/v1/projects")
                        .contentType(MediaType.APPLICATION_JSON)
                        .content("""
                                {
                                  "name": "North Ridge",
                                  "description": "Wind farm project"
                                }
                                """))
                .andExpect(status().isCreated())
                .andExpect(header().string("Location", endsWith("/api/v1/projects/" + projectId)))
                .andExpect(jsonPath("$.id").value(projectId.toString()))
                .andExpect(jsonPath("$.crs").value("EPSG:4326"));
    }

    @Test
    void rejectsProjectWithoutName() throws Exception {
        mockMvc.perform(post("/api/v1/projects")
                        .contentType(MediaType.APPLICATION_JSON)
                        .content("""
                                {
                                  "name": ""
                                }
                                """))
                .andExpect(status().isBadRequest())
                .andExpect(jsonPath("$.message").value("Request validation failed."))
                .andExpect(jsonPath("$.fieldErrors.name").value("Project name is required."));
    }

    @Test
    void returnsNotFoundForUnknownProject() throws Exception {
        UUID projectId = UUID.randomUUID();
        when(projectService.getProject(projectId)).thenThrow(new ProjectNotFoundException(projectId));

        mockMvc.perform(get("/api/v1/projects/{projectId}", projectId))
                .andExpect(status().isNotFound())
                .andExpect(jsonPath("$.status").value(404))
                .andExpect(jsonPath("$.message").value("Project " + projectId + " was not found."));
    }
}
