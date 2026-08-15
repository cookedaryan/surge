package com.power.surge.service;

import com.power.surge.domain.Project;
import com.power.surge.dto.project.CreateProjectRequest;
import com.power.surge.dto.project.ProjectResponse;
import com.power.surge.dto.project.UpdateProjectRequest;
import com.power.surge.repository.ProjectRepository;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.ArgumentCaptor;
import org.mockito.Captor;
import org.mockito.InjectMocks;
import org.mockito.Mock;
import org.mockito.junit.jupiter.MockitoExtension;
import org.springframework.test.util.ReflectionTestUtils;

import java.util.Optional;
import java.util.UUID;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.when;

@ExtendWith(MockitoExtension.class)
class ProjectServiceTest {

    @Mock
    private ProjectRepository projectRepository;

    @Mock
    private AuditLogService auditLogService;

    @Captor
    private ArgumentCaptor<Project> projectCaptor;

    @InjectMocks
    private ProjectService projectService;

    @Test
    void createsProjectFromRequest() {
        Project savedProject = new Project("North Ridge", "Wind farm project");
        // A persisted entity always carries an id; the audit entry references it.
        ReflectionTestUtils.setField(savedProject, "id", UUID.randomUUID());
        when(projectRepository.save(any(Project.class))).thenReturn(savedProject);

        ProjectResponse response = projectService.createProject(
                new CreateProjectRequest("North Ridge", "Wind farm project")
        );

        verify(projectRepository).save(projectCaptor.capture());
        assertThat(projectCaptor.getValue().getName()).isEqualTo("North Ridge");
        assertThat(response.name()).isEqualTo("North Ridge");
        assertThat(response.crs()).isEqualTo(Project.WGS84_CRS);
    }

    @Test
    void updatesExistingProject() {
        UUID projectId = UUID.randomUUID();
        Project project = new Project("North Ridge", "Original description");
        ReflectionTestUtils.setField(project, "id", projectId);
        when(projectRepository.findById(projectId)).thenReturn(Optional.of(project));

        ProjectResponse response = projectService.updateProject(
                projectId,
                new UpdateProjectRequest("North Ridge Extension", "Updated description")
        );

        assertThat(project.getName()).isEqualTo("North Ridge Extension");
        assertThat(response.description()).isEqualTo("Updated description");
    }

    @Test
    void rejectsUnknownProject() {
        UUID projectId = UUID.randomUUID();
        when(projectRepository.findById(projectId)).thenReturn(Optional.empty());

        assertThatThrownBy(() -> projectService.getProject(projectId))
                .isInstanceOf(ProjectNotFoundException.class)
                .hasMessage("Project " + projectId + " was not found.");
    }
}
