package com.power.surge.controller;

import com.power.surge.dto.parcel.CreateParcelRequest;
import com.power.surge.dto.parcel.ParcelResponse;
import com.power.surge.service.ParcelService;
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
@RequestMapping("/api/v1/projects/{projectId}/parcels")
public class CadastralParcelController {

    private final ParcelService parcelService;

    public CadastralParcelController(ParcelService parcelService) {
        this.parcelService = parcelService;
    }

    @PostMapping
    public ResponseEntity<ParcelResponse> createParcel(
            @PathVariable UUID projectId,
            @RequestBody CreateParcelRequest request
    ) {
        ParcelResponse response = parcelService.createParcel(projectId, request);
        return ResponseEntity.status(HttpStatus.CREATED).body(response);
    }

    @PostMapping("/geojson")
    public ResponseEntity<List<ParcelResponse>> importParcelsGeoJson(
            @PathVariable UUID projectId,
            @RequestBody String geoJsonContent
    ) {
        List<ParcelResponse> responses = parcelService.importParcelsGeoJson(projectId, geoJsonContent);
        return ResponseEntity.status(HttpStatus.CREATED).body(responses);
    }

    @GetMapping
    public List<ParcelResponse> getParcels(@PathVariable UUID projectId) {
        return parcelService.getParcels(projectId);
    }

    @GetMapping(value = "/geojson", produces = MediaType.APPLICATION_JSON_VALUE)
    public Map<String, Object> getParcelsGeoJson(@PathVariable UUID projectId) {
        return parcelService.getParcelsGeoJson(projectId);
    }
}
