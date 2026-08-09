package com.power.surge.service;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.power.surge.domain.Project;
import com.power.surge.domain.Substation;
import com.power.surge.domain.WtgLocation;
import com.power.surge.dto.asset.CreateSubstationRequest;
import com.power.surge.dto.asset.CreateWtgRequest;
import com.power.surge.dto.asset.GeoJsonImportResponse;
import com.power.surge.dto.asset.ProjectAssetsResponse;
import com.power.surge.dto.asset.SubstationResponse;
import com.power.surge.dto.asset.WtgResponse;
import com.power.surge.repository.ProjectRepository;
import com.power.surge.repository.SubstationRepository;
import com.power.surge.repository.WtgLocationRepository;
import org.locationtech.jts.geom.Coordinate;
import org.locationtech.jts.geom.GeometryFactory;
import org.locationtech.jts.geom.Point;
import org.locationtech.jts.geom.PrecisionModel;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.math.BigDecimal;
import java.util.ArrayList;
import java.util.HashMap;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.UUID;

@Service
@Transactional(readOnly = true)
public class AssetService {

    private final ProjectRepository projectRepository;
    private final WtgLocationRepository wtgLocationRepository;
    private final SubstationRepository substationRepository;
    private final ObjectMapper objectMapper;
    private final GeometryFactory geometryFactory = new GeometryFactory(new PrecisionModel(), Project.WGS84_SRID);

    public AssetService(
            ProjectRepository projectRepository,
            WtgLocationRepository wtgLocationRepository,
            SubstationRepository substationRepository,
            ObjectMapper objectMapper
    ) {
        this.projectRepository = projectRepository;
        this.wtgLocationRepository = wtgLocationRepository;
        this.substationRepository = substationRepository;
        this.objectMapper = objectMapper;
    }

    @Transactional
    public GeoJsonImportResponse importGeoJson(UUID projectId, String geoJsonContent) {
        Project project = getProjectOrThrow(projectId);

        if (geoJsonContent == null || geoJsonContent.isBlank()) {
            throw new IllegalArgumentException("GeoJSON content must not be blank.");
        }

        JsonNode root;
        try {
            root = objectMapper.readTree(geoJsonContent);
        } catch (Exception e) {
            throw new IllegalArgumentException("Invalid GeoJSON format: " + e.getMessage(), e);
        }

        List<JsonNode> featureNodes = extractFeatures(root);
        List<WtgLocation> wtgEntities = new ArrayList<>();
        List<Substation> substationEntities = new ArrayList<>();

        int wtgCounter = wtgLocationRepository.findAllByProjectIdOrderByExternalIdAsc(projectId).size() + 1;
        int subCounter = substationRepository.findAllByProjectIdOrderByExternalIdAsc(projectId).size() + 1;

        for (JsonNode feature : featureNodes) {
            JsonNode geometry = feature.get("geometry");
            if (geometry == null || geometry.isNull()) {
                continue;
            }

            String geomType = geometry.path("type").asText();
            if (!"Point".equalsIgnoreCase(geomType)) {
                // Skip non-Point features (e.g. LineStrings or Polygons) when importing point assets
                continue;
            }

            JsonNode coords = geometry.get("coordinates");
            if (coords == null || !coords.isArray() || coords.size() < 2) {
                throw new IllegalArgumentException("Point geometry must contain valid [longitude, latitude] coordinates.");
            }

            double longitude = coords.get(0).asDouble();
            double latitude = coords.get(1).asDouble();

            validateCoordinates(longitude, latitude);
            Point point = geometryFactory.createPoint(new Coordinate(longitude, latitude));

            JsonNode properties = feature.path("properties");
            String assetType = extractString(properties, "assetType", "type", "layer");
            String externalId = extractString(feature, "id");
            if (externalId == null) {
                externalId = extractString(properties, "externalId", "external_id", "name", "id");
            }

            BigDecimal capacityMw = extractCapacity(properties);

            boolean isSubstation = assetType != null && assetType.toLowerCase().contains("substation");

            if (isSubstation) {
                if (externalId == null || externalId.isBlank()) {
                    externalId = String.format("SUB-%03d", subCounter++);
                }
                Substation substation = new Substation(project, externalId, capacityMw, point);
                substationEntities.add(substation);
            } else {
                if (externalId == null || externalId.isBlank()) {
                    externalId = String.format("WTG-%03d", wtgCounter++);
                }
                if (capacityMw == null) {
                    capacityMw = new BigDecimal("3.000"); // default 3.0 MW for WTG
                }
                WtgLocation wtg = new WtgLocation(project, externalId, capacityMw, point);
                wtgEntities.add(wtg);
            }
        }

        List<WtgLocation> savedWtgs = wtgLocationRepository.saveAll(wtgEntities);
        List<Substation> savedSubstations = substationRepository.saveAll(substationEntities);

        List<WtgResponse> wtgResponses = savedWtgs.stream().map(this::toWtgResponse).toList();
        List<SubstationResponse> subResponses = savedSubstations.stream().map(this::toSubstationResponse).toList();

        return new GeoJsonImportResponse(
                projectId,
                savedWtgs.size(),
                savedSubstations.size(),
                savedWtgs.size() + savedSubstations.size(),
                wtgResponses,
                subResponses
        );
    }

    @Transactional
    public WtgResponse createWtg(UUID projectId, CreateWtgRequest request) {
        Project project = getProjectOrThrow(projectId);
        Point point = geometryFactory.createPoint(new Coordinate(request.longitude(), request.latitude()));
        WtgLocation wtg = new WtgLocation(project, request.externalId(), request.capacityMw(), point);
        return toWtgResponse(wtgLocationRepository.save(wtg));
    }

    @Transactional
    public SubstationResponse createSubstation(UUID projectId, CreateSubstationRequest request) {
        Project project = getProjectOrThrow(projectId);
        Point point = geometryFactory.createPoint(new Coordinate(request.longitude(), request.latitude()));
        Substation substation = new Substation(project, request.externalId(), request.capacityMw(), point);
        return toSubstationResponse(substationRepository.save(substation));
    }

    public ProjectAssetsResponse getProjectAssets(UUID projectId) {
        getProjectOrThrow(projectId);
        List<WtgResponse> wtgs = wtgLocationRepository.findAllByProjectIdOrderByExternalIdAsc(projectId)
                .stream().map(this::toWtgResponse).toList();
        List<SubstationResponse> substations = substationRepository.findAllByProjectIdOrderByExternalIdAsc(projectId)
                .stream().map(this::toSubstationResponse).toList();

        return new ProjectAssetsResponse(projectId, wtgs.size(), substations.size(), wtgs, substations);
    }

    public List<WtgResponse> listWtgs(UUID projectId) {
        getProjectOrThrow(projectId);
        return wtgLocationRepository.findAllByProjectIdOrderByExternalIdAsc(projectId)
                .stream().map(this::toWtgResponse).toList();
    }

    public List<SubstationResponse> listSubstations(UUID projectId) {
        getProjectOrThrow(projectId);
        return substationRepository.findAllByProjectIdOrderByExternalIdAsc(projectId)
                .stream().map(this::toSubstationResponse).toList();
    }

    public Map<String, Object> getProjectAssetsGeoJson(UUID projectId) {
        getProjectOrThrow(projectId);
        List<WtgLocation> wtgs = wtgLocationRepository.findAllByProjectIdOrderByExternalIdAsc(projectId);
        List<Substation> substations = substationRepository.findAllByProjectIdOrderByExternalIdAsc(projectId);

        List<Map<String, Object>> features = new ArrayList<>();

        for (WtgLocation wtg : wtgs) {
            Map<String, Object> feature = new LinkedHashMap<>();
            feature.put("type", "Feature");
            feature.put("id", wtg.getId().toString());

            Map<String, Object> geometry = new LinkedHashMap<>();
            geometry.put("type", "Point");
            geometry.put("coordinates", List.of(wtg.getLocation().getX(), wtg.getLocation().getY()));
            feature.put("geometry", geometry);

            Map<String, Object> properties = new LinkedHashMap<>();
            properties.put("assetType", "WTG");
            properties.put("externalId", wtg.getExternalId());
            properties.put("capacityMw", wtg.getCapacityMw());
            feature.put("properties", properties);

            features.add(feature);
        }

        for (Substation sub : substations) {
            Map<String, Object> feature = new LinkedHashMap<>();
            feature.put("type", "Feature");
            feature.put("id", sub.getId().toString());

            Map<String, Object> geometry = new LinkedHashMap<>();
            geometry.put("type", "Point");
            geometry.put("coordinates", List.of(sub.getLocation().getX(), sub.getLocation().getY()));
            feature.put("geometry", geometry);

            Map<String, Object> properties = new LinkedHashMap<>();
            properties.put("assetType", "SUBSTATION");
            properties.put("externalId", sub.getExternalId());
            if (sub.getCapacityMw() != null) {
                properties.put("capacityMw", sub.getCapacityMw());
            }
            feature.put("properties", properties);

            features.add(feature);
        }

        Map<String, Object> featureCollection = new LinkedHashMap<>();
        featureCollection.put("type", "FeatureCollection");
        featureCollection.put("features", features);

        return featureCollection;
    }

    private Project getProjectOrThrow(UUID projectId) {
        return projectRepository.findById(projectId)
                .orElseThrow(() -> new ProjectNotFoundException(projectId));
    }

    private WtgResponse toWtgResponse(WtgLocation wtg) {
        return new WtgResponse(
                wtg.getId(),
                wtg.getExternalId(),
                wtg.getCapacityMw(),
                wtg.getLocation().getX(),
                wtg.getLocation().getY(),
                wtg.getCreatedAt()
        );
    }

    private SubstationResponse toSubstationResponse(Substation sub) {
        return new SubstationResponse(
                sub.getId(),
                sub.getExternalId(),
                sub.getCapacityMw(),
                sub.getLocation().getX(),
                sub.getLocation().getY(),
                sub.getCreatedAt()
        );
    }

    private static List<JsonNode> extractFeatures(JsonNode root) {
        String type = root.path("type").asText();
        List<JsonNode> list = new ArrayList<>();
        if ("FeatureCollection".equalsIgnoreCase(type)) {
            JsonNode features = root.get("features");
            if (features != null && features.isArray()) {
                features.forEach(list::add);
            }
        } else if ("Feature".equalsIgnoreCase(type)) {
            list.add(root);
        } else {
            throw new IllegalArgumentException("GeoJSON root type must be 'FeatureCollection' or 'Feature'. Got: " + type);
        }
        return list;
    }

    private static String extractString(JsonNode node, String... keys) {
        if (node == null || node.isMissingNode() || node.isNull()) {
            return null;
        }
        for (String key : keys) {
            JsonNode val = node.get(key);
            if (val != null && !val.isNull() && !val.asText().isBlank()) {
                return val.asText().trim();
            }
        }
        return null;
    }

    private static BigDecimal extractCapacity(JsonNode properties) {
        if (properties == null || properties.isMissingNode() || properties.isNull()) {
            return null;
        }
        String[] keys = {"capacityMw", "capacity_mw", "capacity", "powerMw", "power"};
        for (String key : keys) {
            JsonNode val = properties.get(key);
            if (val != null && !val.isNull()) {
                if (val.isNumber()) {
                    return val.decimalValue();
                } else if (val.isTextual() && !val.asText().isBlank()) {
                    try {
                        return new BigDecimal(val.asText().trim());
                    } catch (NumberFormatException ignored) {
                    }
                }
            }
        }
        return null;
    }

    private static void validateCoordinates(double lon, double lat) {
        if (lon < -180.0 || lon > 180.0) {
            throw new IllegalArgumentException("Longitude must be between -180 and 180 degrees. Got: " + lon);
        }
        if (lat < -90.0 || lat > 90.0) {
            throw new IllegalArgumentException("Latitude must be between -90 and 90 degrees. Got: " + lat);
        }
    }
}
