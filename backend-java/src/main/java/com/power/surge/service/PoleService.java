package com.power.surge.service;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.power.surge.domain.GeneratedPole;
import com.power.surge.domain.JobStatus;
import com.power.surge.domain.OptimizationJob;
import com.power.surge.domain.Project;
import com.power.surge.dto.route.GeneratedPoleResponse;
import com.power.surge.repository.GeneratedPoleRepository;
import com.power.surge.repository.OptimizationJobRepository;
import com.power.surge.repository.ProjectRepository;
import org.locationtech.jts.geom.Coordinate;
import org.locationtech.jts.geom.GeometryFactory;
import org.locationtech.jts.geom.Point;
import org.locationtech.jts.geom.PrecisionModel;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.UUID;

@Service
@Transactional(readOnly = true)
public class PoleService {

    private static final Logger log = LoggerFactory.getLogger(PoleService.class);

    private final ProjectRepository projectRepository;
    private final OptimizationJobRepository jobRepository;
    private final GeneratedPoleRepository poleRepository;
    private final ObjectMapper objectMapper;
    private final GeometryFactory geometryFactory = new GeometryFactory(new PrecisionModel(), Project.WGS84_SRID);

    public PoleService(
            ProjectRepository projectRepository,
            OptimizationJobRepository jobRepository,
            GeneratedPoleRepository poleRepository,
            ObjectMapper objectMapper
    ) {
        this.projectRepository = projectRepository;
        this.jobRepository = jobRepository;
        this.poleRepository = poleRepository;
        this.objectMapper = objectMapper;
    }

    @Transactional
    public List<GeneratedPoleResponse> savePolesFromGeoJson(UUID jobId, Map<String, Object> polesGeoJson) {
        OptimizationJob job = getJobOrThrow(jobId);

        if (polesGeoJson == null || polesGeoJson.isEmpty()) {
            return List.of();
        }

        JsonNode root;
        try {
            root = objectMapper.valueToTree(polesGeoJson);
        } catch (Exception e) {
            log.error("Failed to parse pole GeoJSON for job {}", jobId, e);
            throw new IllegalArgumentException("Invalid GeoJSON payload: " + e.getMessage(), e);
        }

        List<JsonNode> features = extractFeatures(root);
        List<GeneratedPole> entities = new ArrayList<>();
        int poleIndex = 1;

        for (JsonNode feature : features) {
            JsonNode geometry = feature.get("geometry");
            if (geometry == null || geometry.isNull()) {
                continue;
            }

            String geomType = geometry.path("type").asText();
            if (!"Point".equalsIgnoreCase(geomType)) {
                log.warn("Skipping non-Point geometry type: {}", geomType);
                continue;
            }

            JsonNode coordsNode = geometry.get("coordinates");
            if (coordsNode == null || !coordsNode.isArray() || coordsNode.size() < 2) {
                continue;
            }

            Point point = geometryFactory.createPoint(
                    new Coordinate(coordsNode.get(0).asDouble(), coordsNode.get(1).asDouble())
            );

            JsonNode properties = feature.path("properties");
            String poleIdentifier = extractString(properties, "poleId", "pole_id", "id");
            if (poleIdentifier == null || poleIdentifier.isBlank()) {
                poleIdentifier = String.format("POLE-%04d", poleIndex++);
            }

            String feederName = extractString(properties, "feederName", "feeder_name");
            String poleRole = extractString(properties, "poleRole", "pole_role");
            String recommendedPoleType = extractString(properties, "recommendedPoleType", "recommended_pole_type");
            List<String> feederIds = extractStringList(properties, "feederIds", "connected_feeder_ids");
            List<String> routeIds = extractStringList(properties, "connectedRouteIds", "connected_route_ids");

            GeneratedPole pole = new GeneratedPole(
                    job,
                    poleIdentifier,
                    feederName,
                    poleRole,
                    recommendedPoleType,
                    feederIds,
                    routeIds,
                    point
            );
            entities.add(pole);
        }

        List<GeneratedPole> saved = poleRepository.saveAll(entities);
        return saved.stream().map(GeneratedPoleResponse::fromEntity).toList();
    }

    public List<GeneratedPoleResponse> getPolesForJob(UUID projectId, UUID jobId) {
        verifyProjectAndJob(projectId, jobId);
        return poleRepository.findAllByJobIdOrderByPoleIdentifierAsc(jobId)
                .stream()
                .map(GeneratedPoleResponse::fromEntity)
                .toList();
    }

    public Map<String, Object> getPolesGeoJsonForJob(UUID projectId, UUID jobId) {
        verifyProjectAndJob(projectId, jobId);
        List<GeneratedPole> poles = poleRepository.findAllByJobIdOrderByPoleIdentifierAsc(jobId);
        return toFeatureCollection(poles);
    }

    public List<GeneratedPoleResponse> getLatestPolesForProject(UUID projectId) {
        OptimizationJob completedJob = getLatestCompletedJob(projectId);
        return poleRepository.findAllByJobIdOrderByPoleIdentifierAsc(completedJob.getId())
                .stream()
                .map(GeneratedPoleResponse::fromEntity)
                .toList();
    }

    public Map<String, Object> getLatestPolesGeoJsonForProject(UUID projectId) {
        OptimizationJob completedJob = getLatestCompletedJob(projectId);
        List<GeneratedPole> poles = poleRepository.findAllByJobIdOrderByPoleIdentifierAsc(completedJob.getId());
        return toFeatureCollection(poles);
    }

    private OptimizationJob getLatestCompletedJob(UUID projectId) {
        getProjectOrThrow(projectId);
        List<OptimizationJob> jobs = jobRepository.findAllByProjectIdOrderByCreatedAtDesc(projectId);
        return jobs.stream()
                .filter(j -> j.getStatus() == JobStatus.COMPLETED)
                .findFirst()
                .orElseThrow(() -> new IllegalArgumentException("No completed optimization jobs found for project: " + projectId));
    }

    private void verifyProjectAndJob(UUID projectId, UUID jobId) {
        getProjectOrThrow(projectId);
        OptimizationJob job = getJobOrThrow(jobId);
        if (job.getProject().getId() != null && !job.getProject().getId().equals(projectId)) {
            throw new IllegalArgumentException("Job " + jobId + " does not belong to project " + projectId);
        }
    }

    private Project getProjectOrThrow(UUID projectId) {
        return projectRepository.findById(projectId)
                .orElseThrow(() -> new ProjectNotFoundException(projectId));
    }

    private OptimizationJob getJobOrThrow(UUID jobId) {
        return jobRepository.findById(jobId)
                .orElseThrow(() -> new IllegalArgumentException("Optimization job not found: " + jobId));
    }

    private Map<String, Object> toFeatureCollection(List<GeneratedPole> poles) {
        List<Map<String, Object>> features = new ArrayList<>();

        for (GeneratedPole pole : poles) {
            Map<String, Object> feature = new LinkedHashMap<>();
            feature.put("type", "Feature");
            feature.put("id", pole.getId() != null ? pole.getId().toString() : UUID.randomUUID().toString());

            Map<String, Object> geometry = new LinkedHashMap<>();
            geometry.put("type", "Point");
            geometry.put("coordinates", List.of(pole.getLocation().getX(), pole.getLocation().getY()));
            feature.put("geometry", geometry);

            Map<String, Object> properties = new LinkedHashMap<>();
            properties.put("poleId", pole.getPoleIdentifier());
            properties.put("feederName", pole.getFeederName());
            properties.put("feederIds", pole.getConnectedFeederIds());
            properties.put("connectedRouteIds", pole.getConnectedRouteIds());
            properties.put("poleRole", pole.getPoleRole());
            properties.put("recommendedPoleType", pole.getRecommendedPoleType());
            properties.put("jobId", pole.getJob().getId());
            feature.put("properties", properties);

            features.add(feature);
        }

        Map<String, Object> featureCollection = new LinkedHashMap<>();
        featureCollection.put("type", "FeatureCollection");
        featureCollection.put("features", features);
        return featureCollection;
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

    private static List<String> extractStringList(JsonNode node, String... keys) {
        if (node == null || node.isMissingNode() || node.isNull()) {
            return null;
        }
        for (String key : keys) {
            JsonNode val = node.get(key);
            if (val != null && val.isArray()) {
                List<String> values = new ArrayList<>();
                val.forEach(v -> {
                    if (!v.isNull() && !v.asText().isBlank()) {
                        values.add(v.asText().trim());
                    }
                });
                if (!values.isEmpty()) {
                    return values;
                }
            }
        }
        return null;
    }
}
