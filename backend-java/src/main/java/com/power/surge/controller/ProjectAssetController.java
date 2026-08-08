package com.power.surge.controller;

import com.power.surge.dto.asset.CreateSubstationRequest;
import com.power.surge.dto.asset.CreateWtgRequest;
import com.power.surge.dto.asset.GeoJsonImportResponse;
import com.power.surge.dto.asset.ProjectAssetsResponse;
import com.power.surge.dto.asset.SubstationResponse;
import com.power.surge.dto.asset.WtgResponse;
import com.power.surge.service.AssetService;
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
public class ProjectAssetController {

    private final AssetService assetService;

    public ProjectAssetController(AssetService assetService) {
        this.assetService = assetService;
    }

    @PostMapping("/assets/geojson")
    public ResponseEntity<GeoJsonImportResponse> importGeoJson(
            @PathVariable UUID projectId,
            @RequestBody String geoJsonContent
    ) {
        GeoJsonImportResponse response = assetService.importGeoJson(projectId, geoJsonContent);
        return ResponseEntity.status(HttpStatus.CREATED).body(response);
    }

    @GetMapping("/assets")
    public ProjectAssetsResponse getProjectAssets(@PathVariable UUID projectId) {
        return assetService.getProjectAssets(projectId);
    }

    @GetMapping(value = "/assets/geojson", produces = MediaType.APPLICATION_JSON_VALUE)
    public Map<String, Object> getProjectAssetsGeoJson(@PathVariable UUID projectId) {
        return assetService.getProjectAssetsGeoJson(projectId);
    }

    @PostMapping("/wtgs")
    public ResponseEntity<WtgResponse> createWtg(
            @PathVariable UUID projectId,
            @Valid @RequestBody CreateWtgRequest request
    ) {
        WtgResponse response = assetService.createWtg(projectId, request);
        return ResponseEntity.status(HttpStatus.CREATED).body(response);
    }

    @GetMapping("/wtgs")
    public List<WtgResponse> listWtgs(@PathVariable UUID projectId) {
        return assetService.listWtgs(projectId);
    }

    @PostMapping("/substations")
    public ResponseEntity<SubstationResponse> createSubstation(
            @PathVariable UUID projectId,
            @Valid @RequestBody CreateSubstationRequest request
    ) {
        SubstationResponse response = assetService.createSubstation(projectId, request);
        return ResponseEntity.status(HttpStatus.CREATED).body(response);
    }

    @GetMapping("/substations")
    public List<SubstationResponse> listSubstations(@PathVariable UUID projectId) {
        return assetService.listSubstations(projectId);
    }
}
