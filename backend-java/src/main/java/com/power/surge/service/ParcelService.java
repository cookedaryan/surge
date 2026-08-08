package com.power.surge.service;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.power.surge.domain.CadastralParcel;
import com.power.surge.domain.Project;
import com.power.surge.dto.parcel.CreateParcelRequest;
import com.power.surge.dto.parcel.ParcelResponse;
import com.power.surge.repository.CadastralParcelRepository;
import com.power.surge.repository.ProjectRepository;
import org.locationtech.jts.geom.Coordinate;
import org.locationtech.jts.geom.GeometryFactory;
import org.locationtech.jts.geom.LinearRing;
import org.locationtech.jts.geom.Polygon;
import org.locationtech.jts.geom.PrecisionModel;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.math.BigDecimal;
import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.UUID;

@Service
@Transactional(readOnly = true)
public class ParcelService {

    private static final Logger log = LoggerFactory.getLogger(ParcelService.class);

    private final ProjectRepository projectRepository;
    private final CadastralParcelRepository parcelRepository;
    private final ObjectMapper objectMapper;
    private final GeometryFactory geometryFactory = new GeometryFactory(new PrecisionModel(), Project.WGS84_SRID);

    public ParcelService(
            ProjectRepository projectRepository,
            CadastralParcelRepository parcelRepository,
            ObjectMapper objectMapper
    ) {
        this.projectRepository = projectRepository;
        this.parcelRepository = parcelRepository;
        this.objectMapper = objectMapper;
    }

    @Transactional
    public ParcelResponse createParcel(UUID projectId, CreateParcelRequest request) {
        Project project = getProjectOrThrow(projectId);
        Polygon polygon = createPolygon(request.coordinates());
        CadastralParcel parcel = new CadastralParcel(
                project,
                request.parcelId(),
                request.ownerName(),
                request.acquisitionCostPerM2(),
                polygon
        );
        return ParcelResponse.fromEntity(parcelRepository.save(parcel));
    }

    @Transactional
    public List<ParcelResponse> importParcelsGeoJson(UUID projectId, String geoJsonContent) {
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
        List<CadastralParcel> entities = new ArrayList<>();
        int parcelCounter = parcelRepository.findAllByProjectIdOrderByParcelIdAsc(projectId).size() + 1;

        for (JsonNode feature : featureNodes) {
            JsonNode geometry = feature.get("geometry");
            if (geometry == null || geometry.isNull()) {
                continue;
            }

            String geomType = geometry.path("type").asText();
            if (!"Polygon".equalsIgnoreCase(geomType)) {
                log.warn("Skipping non-Polygon geometry type for parcel: {}", geomType);
                continue;
            }

            Polygon polygon = parsePolygonGeometry(geometry);
            JsonNode properties = feature.path("properties");

            String parcelId = extractString(feature, "id");
            if (parcelId == null) {
                parcelId = extractString(properties, "parcelId", "parcel_id", "id", "name");
            }
            if (parcelId == null || parcelId.isBlank()) {
                parcelId = String.format("P-%04d", parcelCounter++);
            }

            String ownerName = extractString(properties, "ownerName", "owner_name", "owner");
            BigDecimal costPerM2 = extractBigDecimal(properties, "acquisitionCostPerM2", "cost_per_m2", "rate_per_m2");

            CadastralParcel parcel = new CadastralParcel(project, parcelId, ownerName, costPerM2, polygon);
            entities.add(parcel);
        }

        List<CadastralParcel> saved = parcelRepository.saveAll(entities);
        return saved.stream().map(ParcelResponse::fromEntity).toList();
    }

    public List<ParcelResponse> getParcels(UUID projectId) {
        getProjectOrThrow(projectId);
        return parcelRepository.findAllByProjectIdOrderByParcelIdAsc(projectId)
                .stream()
                .map(ParcelResponse::fromEntity)
                .toList();
    }

    public Map<String, Object> getParcelsGeoJson(UUID projectId) {
        getProjectOrThrow(projectId);
        List<CadastralParcel> parcels = parcelRepository.findAllByProjectIdOrderByParcelIdAsc(projectId);

        List<Map<String, Object>> features = new ArrayList<>();
        for (CadastralParcel parcel : parcels) {
            Map<String, Object> feature = new LinkedHashMap<>();
            feature.put("type", "Feature");
            feature.put("id", parcel.getId() != null ? parcel.getId().toString() : UUID.randomUUID().toString());

            Map<String, Object> geometry = new LinkedHashMap<>();
            geometry.put("type", "Polygon");

            List<List<List<Double>>> rings = ParcelResponse.fromEntity(parcel).coordinates();
            geometry.put("coordinates", rings);
            feature.put("geometry", geometry);

            Map<String, Object> properties = new LinkedHashMap<>();
            properties.put("parcelId", parcel.getParcelId());
            properties.put("ownerName", parcel.getOwnerName());
            properties.put("acquisitionCostPerM2", parcel.getAcquisitionCostPerM2());
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

    private Polygon createPolygon(List<List<List<Double>>> rings) {
        if (rings == null || rings.isEmpty()) {
            throw new IllegalArgumentException("Polygon coordinates must contain at least one exterior ring.");
        }

        LinearRing shell = createLinearRing(rings.get(0));
        LinearRing[] holes = null;

        if (rings.size() > 1) {
            holes = new LinearRing[rings.size() - 1];
            for (int i = 1; i < rings.size(); i++) {
                holes[i - 1] = createLinearRing(rings.get(i));
            }
        }

        return geometryFactory.createPolygon(shell, holes);
    }

    private Polygon parsePolygonGeometry(JsonNode geomNode) {
        JsonNode coordsNode = geomNode.get("coordinates");
        if (coordsNode == null || !coordsNode.isArray() || coordsNode.isEmpty()) {
            throw new IllegalArgumentException("Polygon geometry missing coordinates array.");
        }

        List<List<List<Double>>> rings = new ArrayList<>();
        for (JsonNode ringNode : coordsNode) {
            if (ringNode.isArray()) {
                List<List<Double>> ringPoints = new ArrayList<>();
                for (JsonNode ptNode : ringNode) {
                    if (ptNode.isArray() && ptNode.size() >= 2) {
                        ringPoints.add(List.of(ptNode.get(0).asDouble(), ptNode.get(1).asDouble()));
                    }
                }
                if (!ringPoints.isEmpty()) {
                    rings.add(ringPoints);
                }
            }
        }
        return createPolygon(rings);
    }

    private LinearRing createLinearRing(List<List<Double>> points) {
        if (points == null || points.size() < 3) {
            throw new IllegalArgumentException("LinearRing must contain at least 3 points.");
        }

        List<Coordinate> coords = new ArrayList<>();
        for (List<Double> pt : points) {
            coords.add(new Coordinate(pt.get(0), pt.get(1)));
        }

        // Close ring if not closed
        if (!coords.get(0).equals2D(coords.get(coords.size() - 1))) {
            coords.add(new Coordinate(coords.get(0).x, coords.get(0).y));
        }

        if (coords.size() < 4) {
            throw new IllegalArgumentException("LinearRing must form a closed loop with at least 4 coordinates.");
        }

        return geometryFactory.createLinearRing(coords.toArray(new Coordinate[0]));
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

    private static BigDecimal extractBigDecimal(JsonNode node, String... keys) {
        if (node == null || node.isMissingNode() || node.isNull()) {
            return null;
        }
        for (String key : keys) {
            JsonNode val = node.get(key);
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
}
