package com.power.surge.controller;

import com.power.surge.dto.restriction.CreateRestrictedAreaRequest;
import com.power.surge.dto.restriction.RestrictedAreaResponse;
import com.power.surge.service.RestrictedAreaService;
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
@RequestMapping("/api/v1/projects/{projectId}/restricted-areas")
public class RestrictedAreaController {

    private final RestrictedAreaService restrictedAreaService;

    public RestrictedAreaController(RestrictedAreaService restrictedAreaService) {
        this.restrictedAreaService = restrictedAreaService;
    }

    @PostMapping
    public ResponseEntity<RestrictedAreaResponse> createRestrictedArea(
            @PathVariable UUID projectId,
            @RequestBody CreateRestrictedAreaRequest request
    ) {
        RestrictedAreaResponse response = restrictedAreaService.createRestrictedArea(projectId, request);
        return ResponseEntity.status(HttpStatus.CREATED).body(response);
    }

    @PostMapping("/geojson")
    public ResponseEntity<List<RestrictedAreaResponse>> importRestrictedAreasGeoJson(
            @PathVariable UUID projectId,
            @RequestBody String geoJsonContent
    ) {
        List<RestrictedAreaResponse> responses = restrictedAreaService.importRestrictedAreasGeoJson(projectId, geoJsonContent);
        return ResponseEntity.status(HttpStatus.CREATED).body(responses);
    }

    @GetMapping
    public List<RestrictedAreaResponse> getRestrictedAreas(@PathVariable UUID projectId) {
        return restrictedAreaService.getRestrictedAreas(projectId);
    }

    @GetMapping(value = "/geojson", produces = MediaType.APPLICATION_JSON_VALUE)
    public Map<String, Object> getRestrictedAreasGeoJson(@PathVariable UUID projectId) {
        return restrictedAreaService.getRestrictedAreasGeoJson(projectId);
    }
}
