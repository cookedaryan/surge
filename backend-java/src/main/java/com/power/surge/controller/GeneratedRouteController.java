package com.power.surge.controller;

import com.power.surge.dto.route.CreateRouteRequest;
import com.power.surge.dto.route.GeneratedRouteResponse;
import com.power.surge.service.RouteService;
import jakarta.validation.Valid;
import org.springframework.http.HttpStatus;
import org.springframework.http.MediaType;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

import java.util.List;
import java.util.Map;
import java.util.UUID;

@RestController
@RequestMapping("/api/v1/projects/{projectId}")
public class GeneratedRouteController {

    private final RouteService routeService;

    public GeneratedRouteController(RouteService routeService) {
        this.routeService = routeService;
    }

    @PostMapping("/jobs/{jobId}/routes")
    public ResponseEntity<List<GeneratedRouteResponse>> createRoutes(
            @PathVariable UUID projectId,
            @PathVariable UUID jobId,
            @RequestBody List<CreateRouteRequest> requests
    ) {
        List<GeneratedRouteResponse> responses = routeService.saveRoutes(jobId, requests);
        return ResponseEntity.status(HttpStatus.CREATED).body(responses);
    }

    @PostMapping("/jobs/{jobId}/routes/geojson")
    public ResponseEntity<List<GeneratedRouteResponse>> importRoutesGeoJson(
            @PathVariable UUID projectId,
            @PathVariable UUID jobId,
            @RequestBody Map<String, Object> feederRoutesGeoJson
    ) {
        List<GeneratedRouteResponse> responses = routeService.saveRoutesFromGeoJson(jobId, feederRoutesGeoJson);
        return ResponseEntity.status(HttpStatus.CREATED).body(responses);
    }

    @GetMapping("/jobs/{jobId}/routes")
    public List<GeneratedRouteResponse> getRoutesForJob(
            @PathVariable UUID projectId,
            @PathVariable UUID jobId
    ) {
        return routeService.getRoutesForJob(projectId, jobId);
    }

    @GetMapping(value = "/jobs/{jobId}/routes/geojson", produces = MediaType.APPLICATION_JSON_VALUE)
    public Map<String, Object> getRoutesGeoJsonForJob(
            @PathVariable UUID projectId,
            @PathVariable UUID jobId
    ) {
        return routeService.getRoutesGeoJsonForJob(projectId, jobId);
    }

    @GetMapping("/routes/latest")
    public List<GeneratedRouteResponse> getLatestRoutesForProject(@PathVariable UUID projectId) {
        return routeService.getLatestRoutesForProject(projectId);
    }

    @GetMapping(value = "/routes/latest/geojson", produces = MediaType.APPLICATION_JSON_VALUE)
    public Map<String, Object> getLatestRoutesGeoJsonForProject(@PathVariable UUID projectId) {
        return routeService.getLatestRoutesGeoJsonForProject(projectId);
    }
}
