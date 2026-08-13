package com.power.surge.controller;

import com.power.surge.dto.route.GeneratedPoleResponse;
import com.power.surge.service.PoleService;
import org.springframework.http.MediaType;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

import java.util.List;
import java.util.Map;
import java.util.UUID;

@RestController
@RequestMapping("/api/v1/projects/{projectId}")
public class GeneratedPoleController {

    private final PoleService poleService;

    public GeneratedPoleController(PoleService poleService) {
        this.poleService = poleService;
    }

    @GetMapping("/jobs/{jobId}/poles")
    public List<GeneratedPoleResponse> getPolesForJob(
            @PathVariable UUID projectId,
            @PathVariable UUID jobId
    ) {
        return poleService.getPolesForJob(projectId, jobId);
    }

    @GetMapping(value = "/jobs/{jobId}/poles/geojson", produces = MediaType.APPLICATION_JSON_VALUE)
    public Map<String, Object> getPolesGeoJsonForJob(
            @PathVariable UUID projectId,
            @PathVariable UUID jobId
    ) {
        return poleService.getPolesGeoJsonForJob(projectId, jobId);
    }

    @GetMapping("/poles/latest")
    public List<GeneratedPoleResponse> getLatestPolesForProject(@PathVariable UUID projectId) {
        return poleService.getLatestPolesForProject(projectId);
    }

    @GetMapping(value = "/poles/latest/geojson", produces = MediaType.APPLICATION_JSON_VALUE)
    public Map<String, Object> getLatestPolesGeoJsonForProject(@PathVariable UUID projectId) {
        return poleService.getLatestPolesGeoJsonForProject(projectId);
    }
}
