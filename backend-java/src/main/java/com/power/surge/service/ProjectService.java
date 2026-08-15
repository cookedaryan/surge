package com.power.surge.service;

import com.power.surge.domain.Project;
import com.power.surge.dto.project.CreateProjectRequest;
import com.power.surge.dto.project.ProjectResponse;
import com.power.surge.dto.project.UpdateProjectRequest;
import com.power.surge.repository.ProjectRepository;
import org.springframework.data.domain.Sort;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.util.List;
import java.util.UUID;

@Service
@Transactional(readOnly = true)
public class ProjectService {

    private final ProjectRepository projectRepository;
    private final AuditLogService auditLogService;

    public ProjectService(ProjectRepository projectRepository, AuditLogService auditLogService) {
        this.projectRepository = projectRepository;
        this.auditLogService = auditLogService;
    }

    @Transactional
    public ProjectResponse createProject(CreateProjectRequest request) {
        Project project = projectRepository.save(new Project(request.name(), request.description()));
        auditLogService.record("PROJECT_CREATED", "PROJECT", String.valueOf(project.getId()),
                "Created project '" + project.getName() + "'");
        return toResponse(project);
    }

    public List<ProjectResponse> listProjects() {
        return projectRepository.findAll(Sort.by(Sort.Direction.ASC, "name"))
                .stream()
                .map(this::toResponse)
                .toList();
    }

    public ProjectResponse getProject(UUID projectId) {
        return toResponse(findProject(projectId));
    }

    @Transactional
    public ProjectResponse updateProject(UUID projectId, UpdateProjectRequest request) {
        Project project = findProject(projectId);
        String previousName = project.getName();
        project.updateDetails(request.name(), request.description());
        auditLogService.record("PROJECT_UPDATED", "PROJECT", String.valueOf(project.getId()),
                previousName.equals(project.getName())
                        ? "Updated project '" + project.getName() + "'"
                        : "Renamed project '" + previousName + "' to '" + project.getName() + "'");
        return toResponse(project);
    }

    private Project findProject(UUID projectId) {
        return projectRepository.findById(projectId)
                .orElseThrow(() -> new ProjectNotFoundException(projectId));
    }

    private ProjectResponse toResponse(Project project) {
        return new ProjectResponse(
                project.getId(),
                project.getName(),
                project.getDescription(),
                project.getCrs(),
                project.getCreatedAt(),
                project.getUpdatedAt()
        );
    }
}
