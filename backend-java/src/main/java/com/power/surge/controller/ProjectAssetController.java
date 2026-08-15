package com.power.surge.controller;

import com.fasterxml.jackson.databind.ObjectMapper;
import com.power.surge.dto.asset.AssetImportPreviewResponse;
import com.power.surge.dto.asset.CommitAssetImportRequest;
import com.power.surge.dto.asset.CreateSubstationRequest;
import com.power.surge.dto.asset.CreateWtgRequest;
import com.power.surge.dto.asset.EvacuationTowerResponse;
import com.power.surge.dto.asset.GeoJsonImportResponse;
import com.power.surge.dto.asset.ProjectAssetsResponse;
import com.power.surge.dto.asset.ReferenceLineResponse;
import com.power.surge.dto.asset.SubstationResponse;
import com.power.surge.dto.asset.WtgResponse;
import com.power.surge.service.AssetService;
import com.power.surge.service.KmzConversionResult;
import com.power.surge.service.KmzGeoJsonConverter;
import jakarta.validation.Valid;
import org.springframework.http.HttpStatus;
import org.springframework.http.MediaType;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;
import org.springframework.web.multipart.MultipartFile;

import java.util.List;
import java.util.Map;
import java.util.UUID;

@RestController
@RequestMapping("/api/v1/projects/{projectId}")
public class ProjectAssetController {

    private final AssetService assetService;
    private final KmzGeoJsonConverter kmzConverter;
    private final ObjectMapper objectMapper;

    public ProjectAssetController(
            AssetService assetService,
            KmzGeoJsonConverter kmzConverter,
            ObjectMapper objectMapper
    ) {
        this.assetService = assetService;
        this.kmzConverter = kmzConverter;
        this.objectMapper = objectMapper;
    }

    @PostMapping("/assets/geojson")
    public ResponseEntity<GeoJsonImportResponse> importGeoJson(
            @PathVariable UUID projectId,
            @RequestBody String geoJsonContent
    ) {
        GeoJsonImportResponse response = assetService.importGeoJson(projectId, geoJsonContent);
        return ResponseEntity.status(HttpStatus.CREATED).body(response);
    }

    /**
     * Classifies an uploaded KMZ/KML without persisting anything.
     *
     * <p>This is the recommended entry point. The response lists every placemark with the asset type
     * it resolved to and the rule that decided it, so a misdetection is corrected before it reaches
     * the database rather than cleaned up afterwards.</p>
     */
    @PostMapping(value = "/assets/kmz/preview", consumes = MediaType.MULTIPART_FORM_DATA_VALUE)
    public AssetImportPreviewResponse previewKmzAssets(
            @PathVariable UUID projectId,
            @RequestParam("file") MultipartFile file
    ) {
        KmzConversionResult conversion = kmzConverter.convert(readBytes(file));
        return assetService.previewImport(
                projectId,
                file.getOriginalFilename(),
                conversion.featureCollection(),
                conversion.duplicatesRemoved(),
                conversion.skippedByGeometry()
        );
    }

    /** Persists a previewed import, applying any per-feature overrides the user made. */
    @PostMapping("/assets/import/commit")
    public ResponseEntity<GeoJsonImportResponse> commitAssetImport(
            @PathVariable UUID projectId,
            @Valid @RequestBody CommitAssetImportRequest request
    ) {
        return ResponseEntity.status(HttpStatus.CREATED).body(assetService.commitImport(projectId, request));
    }

    /**
     * Single-step KMZ import.
     *
     * <p>Retained for backwards compatibility. Unlike the previous implementation it refuses to
     * persist features it cannot classify instead of defaulting them to turbines; prefer the
     * preview/commit pair for files whose structure is not known in advance.</p>
     */
    @PostMapping(value = "/assets/kmz", consumes = MediaType.MULTIPART_FORM_DATA_VALUE)
    public ResponseEntity<GeoJsonImportResponse> importKmzAssets(
            @PathVariable UUID projectId,
            @RequestParam("file") MultipartFile file
    ) {
        KmzConversionResult conversion = kmzConverter.convert(readBytes(file));
        String geoJsonContent;
        try {
            geoJsonContent = objectMapper.writeValueAsString(conversion.featureCollection());
        } catch (Exception e) {
            throw new IllegalArgumentException("Failed to serialize GeoJSON: " + e.getMessage(), e);
        }
        GeoJsonImportResponse response = assetService.importGeoJson(
                projectId, geoJsonContent, "One-step KMZ/KML upload of '" + file.getOriginalFilename() + "'");
        return ResponseEntity.status(HttpStatus.CREATED).body(response);
    }

    private static byte[] readBytes(MultipartFile file) {
        if (file == null || file.isEmpty()) {
            throw new IllegalArgumentException("Multipart file must not be empty.");
        }
        try {
            return file.getBytes();
        } catch (Exception e) {
            throw new IllegalArgumentException("Failed to read uploaded file: " + e.getMessage(), e);
        }
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

    @GetMapping("/towers")
    public List<EvacuationTowerResponse> listTowers(@PathVariable UUID projectId) {
        return assetService.listTowers(projectId);
    }

    /** Existing roads, HT/EHV lines, watercourses and prior routes imported from survey files. */
    @GetMapping("/reference-lines")
    public List<ReferenceLineResponse> listReferenceLines(@PathVariable UUID projectId) {
        return assetService.listLines(projectId);
    }
}
