package com.power.surge.service;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.power.surge.domain.GeneratedPole;
import com.power.surge.domain.GeneratedRoute;
import com.power.surge.domain.JobStatus;
import com.power.surge.domain.OptimizationJob;
import com.power.surge.domain.Project;
import com.power.surge.dto.route.CreateRouteRequest;
import com.power.surge.dto.route.GeneratedRouteResponse;
import com.power.surge.repository.GeneratedPoleRepository;
import com.power.surge.repository.GeneratedRouteRepository;
import com.power.surge.repository.OptimizationJobRepository;
import com.power.surge.repository.ProjectRepository;
import org.locationtech.jts.geom.Coordinate;
import org.locationtech.jts.geom.GeometryFactory;
import org.locationtech.jts.geom.LineString;
import org.locationtech.jts.geom.MultiPoint;
import org.locationtech.jts.geom.Point;
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
public class RouteService {

    private static final Logger log = LoggerFactory.getLogger(RouteService.class);

    private final ProjectRepository projectRepository;
    private final OptimizationJobRepository jobRepository;
    private final GeneratedRouteRepository routeRepository;
    private final GeneratedPoleRepository poleRepository;
    private final ObjectMapper objectMapper;
    private final GeometryFactory geometryFactory = new GeometryFactory(new PrecisionModel(), Project.WGS84_SRID);

    public RouteService(
            ProjectRepository projectRepository,
            OptimizationJobRepository jobRepository,
            GeneratedRouteRepository routeRepository,
            GeneratedPoleRepository poleRepository,
            ObjectMapper objectMapper
    ) {
        this.projectRepository = projectRepository;
        this.jobRepository = jobRepository;
        this.routeRepository = routeRepository;
        this.poleRepository = poleRepository;
        this.objectMapper = objectMapper;
    }

    @Transactional
    public List<GeneratedRouteResponse> saveRoutes(UUID jobId, List<CreateRouteRequest> requests) {
        OptimizationJob job = getJobOrThrow(jobId);

        List<GeneratedRoute> entities = new ArrayList<>();
        int feederIndex = 1;

        for (CreateRouteRequest req : requests) {
            String feederName = req.feederName() != null && !req.feederName().isBlank()
                    ? req.feederName()
                    : String.format("Feeder-%02d", feederIndex++);

            LineString lineString = createLineString(req.coordinates());
            MultiPoint multiPoint = req.poleCoordinates() != null && !req.poleCoordinates().isEmpty()
                    ? createMultiPoint(req.poleCoordinates())
                    : null;

            BigDecimal length = req.totalLengthMeters() != null
                    ? req.totalLengthMeters()
                    : BigDecimal.valueOf(calculateLineStringLengthMeters(lineString));

            GeneratedRoute route = new GeneratedRoute(
                    job,
                    feederName,
                    length,
                    req.totalCost(),
                    req.electricalLossesKw(),
                    req.poleCount() != null ? req.poleCount() : 0,
                    lineString,
                    multiPoint,
                    null
            );
            entities.add(route);
        }

        List<GeneratedRoute> saved = routeRepository.saveAll(entities);
        return saved.stream().map(GeneratedRouteResponse::fromEntity).toList();
    }

    @Transactional
    public List<GeneratedRouteResponse> saveRoutesFromGeoJson(UUID jobId, Map<String, Object> feederRoutesGeoJson) {
        return saveRoutesFromGeoJson(jobId, feederRoutesGeoJson, Map.of(), Map.of());
    }

    public List<GeneratedRouteResponse> saveRoutesFromGeoJson(
            UUID jobId,
            Map<String, Object> feederRoutesGeoJson,
            Map<String, CableSelection> cableBySegment
    ) {
        return saveRoutesFromGeoJson(jobId, feederRoutesGeoJson, cableBySegment, Map.of());
    }

    /**
     * @param cableBySegment       conductor selected per segment id, empty when the run reported none.
     *                             Kept separate from the GeoJSON because the engine reports sizing on
     *                             the candidate rather than on the geometry.
     * @param conductorCostBySegment what the engine priced each segment's conductor at, empty when the
     *                             run was not costed. Also reported on the candidate, and the only
     *                             cost component attributable to an individual route.
     */
    public List<GeneratedRouteResponse> saveRoutesFromGeoJson(
            UUID jobId,
            Map<String, Object> feederRoutesGeoJson,
            Map<String, CableSelection> cableBySegment,
            Map<String, BigDecimal> conductorCostBySegment
    ) {
        OptimizationJob job = getJobOrThrow(jobId);

        if (feederRoutesGeoJson == null || feederRoutesGeoJson.isEmpty()) {
            return List.of();
        }

        JsonNode root;
        try {
            root = objectMapper.valueToTree(feederRoutesGeoJson);
        } catch (Exception e) {
            log.error("Failed to parse GeoJSON for job {}", jobId, e);
            throw new IllegalArgumentException("Invalid GeoJSON payload: " + e.getMessage(), e);
        }

        List<JsonNode> features = extractFeatures(root);
        List<GeneratedRoute> entities = new ArrayList<>();
        int feederIndex = 1;

        for (JsonNode feature : features) {
            JsonNode geometry = feature.get("geometry");
            if (geometry == null || geometry.isNull()) {
                continue;
            }

            String geomType = geometry.path("type").asText();
            if (!"LineString".equalsIgnoreCase(geomType)) {
                log.warn("Skipping non-LineString geometry type: {}", geomType);
                continue;
            }

            JsonNode coordsNode = geometry.get("coordinates");
            if (coordsNode == null || !coordsNode.isArray() || coordsNode.size() < 2) {
                continue;
            }

            List<Coordinate> coordsList = new ArrayList<>();
            for (JsonNode pt : coordsNode) {
                if (pt.isArray() && pt.size() >= 2) {
                    coordsList.add(new Coordinate(pt.get(0).asDouble(), pt.get(1).asDouble()));
                }
            }

            if (coordsList.size() < 2) {
                continue;
            }

            LineString lineString = geometryFactory.createLineString(coordsList.toArray(new Coordinate[0]));

            JsonNode properties = feature.path("properties");
            String feederName = extractString(properties, "feederName", "feeder_name", "name", "id");
            if (feederName == null || feederName.isBlank()) {
                feederName = String.format("Feeder-%02d", feederIndex++);
            }

            BigDecimal totalLength = extractBigDecimal(properties, "totalLengthMeters", "total_length_m", "length_m");
            if (totalLength == null) {
                totalLength = BigDecimal.valueOf(calculateLineStringLengthMeters(lineString));
            }

            // No fabricated fallback. This used to be length x 80 -- a constant with no basis, no
            // currency and no provenance, which then flowed into the BOM total, the scenario
            // comparison and the route popups as though it were an estimate. A route the engine did
            // not price has an unknown cost, and null is how that is said. The real per-segment
            // conductor cost is applied separately, from the engine's own line items.
            BigDecimal totalCost = extractBigDecimal(properties, "totalCost", "total_cost", "cost");

            BigDecimal lossesKw = extractBigDecimal(properties, "electricalLossesKw", "electrical_losses_kw", "losses_kw");
            if (lossesKw == null) {
                lossesKw = BigDecimal.valueOf(Math.round(totalLength.doubleValue() * 0.005 * 100.0) / 100.0);
            }

            Integer poleCount = extractInteger(properties, "poleCount", "pole_count", "poles");
            if (poleCount == null || poleCount <= 0) {
                poleCount = Math.max(2, (int) Math.ceil(totalLength.doubleValue() / 150.0) + 1);
            }

            String segmentId = extractString(properties, "segmentId", "segment_id");

            GeneratedRoute route = new GeneratedRoute(
                    job,
                    feederName,
                    totalLength,
                    totalCost,
                    lossesKw,
                    poleCount,
                    lineString,
                    null,
                    segmentId
            );

            CableSelection cable = segmentId != null ? cableBySegment.get(segmentId) : null;
            if (cable != null) {
                route.applyCableSelection(
                        cable.cableTypeId(),
                        cable.requiredCurrentA(),
                        cable.effectiveAmpacityA(),
                        cable.utilisationPct()
                );
            }
            if (segmentId != null) {
                // Left null when the engine priced nothing for this segment, rather than zeroed:
                // an unpriced conductor is unknown, not free.
                route.applyConductorCost(conductorCostBySegment.get(segmentId));
            }
            entities.add(route);
        }

        List<GeneratedRoute> saved = routeRepository.saveAll(entities);
        return saved.stream().map(GeneratedRouteResponse::fromEntity).toList();
    }

    public List<GeneratedRouteResponse> getRoutesForJob(UUID projectId, UUID jobId) {
        verifyProjectAndJob(projectId, jobId);
        return routeRepository.findAllByJobIdOrderByFeederNameAsc(jobId)
                .stream()
                .map(GeneratedRouteResponse::fromEntity)
                .toList();
    }

    public Map<String, Object> getRoutesGeoJsonForJob(UUID projectId, UUID jobId) {
        verifyProjectAndJob(projectId, jobId);
        List<GeneratedRoute> routes = routeRepository.findAllByJobIdOrderByFeederNameAsc(jobId);
        return toFeatureCollection(routes);
    }

    public List<GeneratedRouteResponse> getLatestRoutesForProject(UUID projectId) {
        getProjectOrThrow(projectId);
        List<OptimizationJob> jobs = jobRepository.findAllByProjectIdOrderByCreatedAtDesc(projectId);
        OptimizationJob completedJob = jobs.stream()
                .filter(j -> j.getStatus() == JobStatus.COMPLETED)
                .findFirst()
                .orElseThrow(() -> new IllegalArgumentException("No completed optimization jobs found for project: " + projectId));

        return routeRepository.findAllByJobIdOrderByFeederNameAsc(completedJob.getId())
                .stream()
                .map(GeneratedRouteResponse::fromEntity)
                .toList();
    }

    public Map<String, Object> getLatestRoutesGeoJsonForProject(UUID projectId) {
        getProjectOrThrow(projectId);
        List<OptimizationJob> jobs = jobRepository.findAllByProjectIdOrderByCreatedAtDesc(projectId);
        OptimizationJob completedJob = jobs.stream()
                .filter(j -> j.getStatus() == JobStatus.COMPLETED)
                .findFirst()
                .orElseThrow(() -> new IllegalArgumentException("No completed optimization jobs found for project: " + projectId));

        List<GeneratedRoute> routes = routeRepository.findAllByJobIdOrderByFeederNameAsc(completedJob.getId());
        return toFeatureCollection(routes);
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

    private LineString createLineString(List<List<Double>> points) {
        if (points == null || points.size() < 2) {
            throw new IllegalArgumentException("LineString coordinates must contain at least 2 points.");
        }
        Coordinate[] coords = new Coordinate[points.size()];
        for (int i = 0; i < points.size(); i++) {
            List<Double> pt = points.get(i);
            if (pt == null || pt.size() < 2) {
                throw new IllegalArgumentException("Coordinate point must contain [longitude, latitude].");
            }
            coords[i] = new Coordinate(pt.get(0), pt.get(1));
        }
        return geometryFactory.createLineString(coords);
    }

    private MultiPoint createMultiPoint(List<List<Double>> points) {
        Point[] pts = new Point[points.size()];
        for (int i = 0; i < points.size(); i++) {
            List<Double> pt = points.get(i);
            pts[i] = geometryFactory.createPoint(new Coordinate(pt.get(0), pt.get(1)));
        }
        return geometryFactory.createMultiPoint(pts);
    }

    private Map<String, Object> toFeatureCollection(List<GeneratedRoute> routes) {
        List<Map<String, Object>> features = new ArrayList<>();
        Map<String, Long> poleCountBySegment = routes.isEmpty()
                ? Map.of()
                : poleCountBySegmentId(routes.get(0).getJob().getId());

        for (GeneratedRoute route : routes) {
            Map<String, Object> feature = new LinkedHashMap<>();
            feature.put("type", "Feature");
            feature.put("id", route.getId() != null ? route.getId().toString() : UUID.randomUUID().toString());

            Map<String, Object> geometry = new LinkedHashMap<>();
            geometry.put("type", "LineString");

            List<List<Double>> coords = new ArrayList<>();
            if (route.getRoutePath() != null) {
                for (Coordinate c : route.getRoutePath().getCoordinates()) {
                    coords.add(List.of(c.getX(), c.getY()));
                }
            }
            geometry.put("coordinates", coords);
            feature.put("geometry", geometry);

            // Prefer the real placed-pole count for this exact segment over the /150m estimate
            // stored on the route at save time; not every route has a matching segmentId (older
            // jobs, or the manual CreateRouteRequest path), so fall back when there's no match.
            Long realPoleCount = route.getSegmentId() != null ? poleCountBySegment.get(route.getSegmentId()) : null;

            Map<String, Object> properties = new LinkedHashMap<>();
            properties.put("feederName", route.getFeederName());
            properties.put("totalLengthMeters", route.getTotalLengthMeters());
            properties.put("totalCost", route.getTotalCost());
            // The engine's own figure for this segment's conductor, which is the only cost it
            // attributes to a single route. Null where nothing was priced.
            properties.put("conductorCost", route.getConductorCost());
            // Read from the route's own job so this works wherever the collection is built.
            properties.put("costCurrency",
                    route.getJob() != null ? route.getJob().getCostCurrency() : null);
            properties.put("electricalLossesKw", route.getElectricalLossesKw());
            properties.put("poleCount", realPoleCount != null ? realPoleCount.intValue() : route.getPoleCount());
            // The conductor chosen for this segment, and how hard it is working. Persisted since
            // the cable-sizing wiring but only ever visible in the BOM exports, so an engineer
            // clicking a line on the map could not see what it was made of.
            properties.put("cableTypeId", route.getCableTypeId());
            properties.put("cableUtilisationPct", route.getCableUtilisationPct());
            properties.put("cableRequiredCurrentA", route.getCableRequiredCurrentA());
            properties.put("cableEffectiveAmpacityA", route.getCableEffectiveAmpacityA());
            properties.put("segmentId", route.getSegmentId());
            properties.put("jobId", route.getJob().getId());
            feature.put("properties", properties);

            features.add(feature);
        }

        Map<String, Object> featureCollection = new LinkedHashMap<>();
        featureCollection.put("type", "FeatureCollection");
        featureCollection.put("features", features);
        return featureCollection;
    }

    /**
     * Counts real placed poles per segment_id for a job. A junction pole can carry more than one
     * segment_id (it's shared between the two edges that meet there), so it's counted once toward
     * each — matching what a rider would actually see standing at each individual segment.
     */
    private Map<String, Long> poleCountBySegmentId(UUID jobId) {
        Map<String, Long> counts = new LinkedHashMap<>();
        for (GeneratedPole pole : poleRepository.findAllByJobIdOrderByPoleIdentifierAsc(jobId)) {
            List<String> routeIds = pole.getConnectedRouteIds();
            if (routeIds == null) {
                continue;
            }
            for (String routeId : routeIds) {
                counts.merge(routeId, 1L, Long::sum);
            }
        }
        return counts;
    }

    private static double calculateLineStringLengthMeters(LineString lineString) {
        // Approximate planar metric length (haversine calculation for geographic points)
        double totalMeters = 0.0;
        Coordinate[] coords = lineString.getCoordinates();
        for (int i = 0; i < coords.length - 1; i++) {
            totalMeters += haversineDistanceMeters(coords[i].getY(), coords[i].getX(), coords[i + 1].getY(), coords[i + 1].getX());
        }
        return totalMeters;
    }

    private static double haversineDistanceMeters(double lat1, double lon1, double lat2, double lon2) {
        final int R = 6371000; // Earth radius in meters
        double dLat = Math.toRadians(lat2 - lat1);
        double dLon = Math.toRadians(lon2 - lon1);
        double a = Math.sin(dLat / 2) * Math.sin(dLat / 2)
                + Math.cos(Math.toRadians(lat1)) * Math.cos(Math.toRadians(lat2))
                * Math.sin(dLon / 2) * Math.sin(dLon / 2);
        double c = 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1 - a));
        return R * c;
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

    private static Integer extractInteger(JsonNode node, String... keys) {
        if (node == null || node.isMissingNode() || node.isNull()) {
            return null;
        }
        for (String key : keys) {
            JsonNode val = node.get(key);
            if (val != null && !val.isNull() && val.isInt()) {
                return val.asInt();
            }
        }
        return null;
    }
}
