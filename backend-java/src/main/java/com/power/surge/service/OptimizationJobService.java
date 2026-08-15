package com.power.surge.service;

import com.fasterxml.jackson.databind.ObjectMapper;
import com.power.surge.client.PythonOptimizationClient;
import com.power.surge.domain.CadastralParcel;
import com.power.surge.domain.LineType;
import com.power.surge.domain.OptimizationJob;
import com.power.surge.domain.Project;
import com.power.surge.domain.ReferenceLine;
import com.power.surge.domain.RestrictedArea;
import com.power.surge.domain.Substation;
import com.power.surge.domain.WtgLocation;
import com.power.surge.dto.client.python.PythonOptimisationRequest;
import com.power.surge.dto.client.python.PythonOptimisationResponse;
import com.power.surge.dto.job.CreateOptimizationJobRequest;
import com.power.surge.dto.job.OptimizationJobResponse;
import com.power.surge.repository.CadastralParcelRepository;
import com.power.surge.repository.GeneratedRouteRepository;
import com.power.surge.repository.OptimizationJobRepository;
import com.power.surge.repository.ProjectRepository;
import com.power.surge.repository.ReferenceLineRepository;
import com.power.surge.repository.RestrictedAreaRepository;
import com.power.surge.repository.SubstationRepository;
import com.power.surge.repository.WtgLocationRepository;
import org.locationtech.jts.geom.Coordinate;
import org.locationtech.jts.geom.Polygon;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.math.BigDecimal;
import java.util.ArrayList;
import java.util.Comparator;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.UUID;

@Service
@Transactional(readOnly = true)
public class OptimizationJobService {

    private static final Logger log = LoggerFactory.getLogger(OptimizationJobService.class);

    private final ProjectRepository projectRepository;
    private final OptimizationJobRepository jobRepository;
    private final GeneratedRouteRepository routeRepository;
    private final WtgLocationRepository wtgLocationRepository;
    private final SubstationRepository substationRepository;
    private final ReferenceLineRepository referenceLineRepository;
    private final CadastralParcelRepository parcelRepository;
    private final RestrictedAreaRepository restrictedAreaRepository;
    private final RouteService routeService;
    private final PoleService poleService;
    private final PythonOptimizationClient pythonClient;
    private final ObjectMapper objectMapper;
    private final SseProgressService sseProgressService;
    private final AuditLogService auditLogService;

    public OptimizationJobService(
            ProjectRepository projectRepository,
            OptimizationJobRepository jobRepository,
            GeneratedRouteRepository routeRepository,
            WtgLocationRepository wtgLocationRepository,
            SubstationRepository substationRepository,
            ReferenceLineRepository referenceLineRepository,
            CadastralParcelRepository parcelRepository,
            RestrictedAreaRepository restrictedAreaRepository,
            RouteService routeService,
            PoleService poleService,
            PythonOptimizationClient pythonClient,
            ObjectMapper objectMapper,
            SseProgressService sseProgressService,
            AuditLogService auditLogService
    ) {
        this.projectRepository = projectRepository;
        this.jobRepository = jobRepository;
        this.routeRepository = routeRepository;
        this.wtgLocationRepository = wtgLocationRepository;
        this.substationRepository = substationRepository;
        this.referenceLineRepository = referenceLineRepository;
        this.parcelRepository = parcelRepository;
        this.restrictedAreaRepository = restrictedAreaRepository;
        this.routeService = routeService;
        this.poleService = poleService;
        this.pythonClient = pythonClient;
        this.objectMapper = objectMapper;
        this.sseProgressService = sseProgressService;
        this.auditLogService = auditLogService;
    }

    @Transactional
    public OptimizationJobResponse createAndRunJob(UUID projectId, CreateOptimizationJobRequest request) {
        Project project = getProjectOrThrow(projectId);

        List<WtgLocation> allWtgs = wtgLocationRepository.findAllByProjectIdOrderByExternalIdAsc(projectId);
        List<Substation> substations = substationRepository.findAllByProjectIdOrderByExternalIdAsc(projectId);

        // Cancelled, low-AEP and to-be-shifted locations are stored and rendered but must not reach
        // the optimiser: including them inflates the feeder count and distorts the MST topology.
        List<WtgLocation> wtgs = allWtgs.stream()
                .filter(wtg -> wtg.getStatus().isOptimisable())
                .toList();

        if (allWtgs.isEmpty()) {
            throw new IllegalArgumentException("Cannot run optimization: Project has no WTG locations.");
        }
        if (wtgs.isEmpty()) {
            throw new IllegalArgumentException(
                    "Cannot run optimization: none of the " + allWtgs.size() + " turbine location(s) in this "
                            + "project have an optimisable status (APPROVED, REGISTRATION or PROPOSED).");
        }
        if (substations.isEmpty()) {
            throw new IllegalArgumentException("Cannot run optimization: Project has no substations.");
        }

        CreateOptimizationJobRequest req = request != null ? request : new CreateOptimizationJobRequest(
                "MULTI_OBJECTIVE_A_STAR", "Balanced", null, null, null, null, null, null, null
        );

        OptimizationJob job = new OptimizationJob(
                project,
                req.algorithmType() != null ? req.algorithmType() : "MULTI_OBJECTIVE_A_STAR",
                req.scenario() != null ? req.scenario() : "Balanced",
                req.capexWeight() != null ? req.capexWeight() : new BigDecimal("0.5000"),
                req.lossesWeight() != null ? req.lossesWeight() : new BigDecimal("0.5000"),
                req.maxSpanMeters() != null ? req.maxSpanMeters() : new BigDecimal("150.00"),
                req.voltageKv() != null ? req.voltageKv() : new BigDecimal("33.00")
        );

        job = jobRepository.save(job);
        job.markRunning();
        sseProgressService.emitProgress(job.getId(), 10, "Validating project assets and spatial constraints", com.power.surge.domain.JobStatus.RUNNING);

        try {
            sseProgressService.emitProgress(job.getId(), 35, "Serializing GeoJSON & dispatching request to Python FastAPI Engine", com.power.surge.domain.JobStatus.RUNNING);
            Map<String, Object> wtgGeoJson = buildWtgGeoJson(wtgs);
            Map<String, Object> subGeoJson = buildSubstationGeoJson(substations, wtgs);

            String scenario = req.scenario() != null ? req.scenario() : ScenarioProfile.BALANCED;
            // The scenario is not just a label: it selects the candidate scoring weights AND the
            // constraint cost/clearance bias applied to the A* surface. See ScenarioProfile.
            ScenarioProfile profile = ScenarioProfile.forScenario(scenario);

            Map<String, Object> electricalParams = new LinkedHashMap<>();
            electricalParams.put("feeder_capacity_mw", req.feederCapacityMw() != null ? req.feederCapacityMw().doubleValue() : 20.0);
            electricalParams.put("max_voltage_drop_pct", req.maxVoltageDropPct() != null ? req.maxVoltageDropPct().doubleValue() : 5.0);
            electricalParams.put("row_width_m", req.rowWidthM() != null ? req.rowWidthM().doubleValue() : 18.0);
            electricalParams.put("nominal_voltage_kv", req.voltageKv() != null ? req.voltageKv().doubleValue() : 33.0);

            // Scaled from the user's chosen max span using the same target/min ratios as the
            // Python engine's own defaults (target_span_m=100/max_span_m=120, min_span_m=30/
            // max_span_m=120), so the pole-placement engine actually honours the "Max pole span"
            // control instead of silently falling back to those hardcoded defaults.
            double maxSpanM = req.maxSpanMeters() != null ? req.maxSpanMeters().doubleValue() : 150.0;
            Map<String, Object> poleConfig = new LinkedHashMap<>();
            poleConfig.put("max_span_m", maxSpanM);
            poleConfig.put("target_span_m", maxSpanM * (100.0 / 120.0));
            poleConfig.put("min_span_m", maxSpanM * (30.0 / 120.0));

            Map<String, Object> avoidanceGeoJson = buildAvoidanceGeoJson(projectId, profile);

            PythonOptimisationRequest pythonReq = new PythonOptimisationRequest(
                    "job-" + job.getId(),
                    projectId.toString(),
                    scenario,
                    wtgGeoJson,
                    subGeoJson,
                    electricalParams,
                    poleConfig,
                    avoidanceGeoJson,
                    profile.scoringWeights()
            );

            PythonOptimisationResponse pythonResp = pythonClient.runOptimization(pythonReq);

            sseProgressService.emitProgress(job.getId(), 70, "Processing radial feeder topology and route outputs", com.power.surge.domain.JobStatus.RUNNING);
            String summaryJson = objectMapper.writeValueAsString(buildResultSummary(pythonResp));

            if ("success".equalsIgnoreCase(pythonResp.status())) {
                if (pythonResp.feederRoutesGeojson() != null && !pythonResp.feederRoutesGeojson().isEmpty()) {
                    sseProgressService.emitProgress(job.getId(), 85, "Saving route geometries and pole locations to PostGIS", com.power.surge.domain.JobStatus.RUNNING);
                    routeService.saveRoutesFromGeoJson(job.getId(), pythonResp.feederRoutesGeojson());
                }
                if (pythonResp.polesGeojson() != null && !pythonResp.polesGeojson().isEmpty()) {
                    poleService.savePolesFromGeoJson(job.getId(), pythonResp.polesGeojson());
                }
                job.markCompleted(summaryJson);
                auditLogService.record("OPTIMIZATION_COMPLETED", "JOB", String.valueOf(job.getId()),
                        "Scenario '" + scenario + "' completed for project '" + project.getName() + "' ("
                                + wtgs.size() + " optimisable WTG, " + voltage(req) + " kV)");
                sseProgressService.completeProgress(job.getId(), "Optimization job completed successfully!", true);
            } else {
                String errMsg = describeFailure(pythonResp);
                job.markFailed(errMsg, summaryJson);
                auditLogService.record("OPTIMIZATION_FAILED", "JOB", String.valueOf(job.getId()),
                        "Scenario '" + scenario + "' failed for project '" + project.getName() + "': " + errMsg);
                sseProgressService.completeProgress(job.getId(), errMsg, false);
            }

        } catch (Exception e) {
            log.error("Failed to run optimization job {}", job.getId(), e);
            String errMsg = "Error dispatching optimization job: " + e.getMessage();
            job.markFailed(errMsg);
            auditLogService.record("OPTIMIZATION_FAILED", "JOB", String.valueOf(job.getId()),
                    "Job for project '" + project.getName() + "' failed: " + errMsg);
            sseProgressService.completeProgress(job.getId(), errMsg, false);
        }

        return OptimizationJobResponse.fromEntity(jobRepository.save(job));
    }

    public OptimizationJobResponse getJob(UUID projectId, UUID jobId) {
        getProjectOrThrow(projectId);
        OptimizationJob job = jobRepository.findById(jobId)
                .orElseThrow(() -> new IllegalArgumentException("Optimization job not found: " + jobId));

        if (job.getProject().getId() != null && !job.getProject().getId().equals(projectId)) {
            throw new IllegalArgumentException("Job " + jobId + " does not belong to project " + projectId);
        }

        return OptimizationJobResponse.fromEntity(job);
    }

    public List<OptimizationJobResponse> listJobs(UUID projectId) {
        getProjectOrThrow(projectId);
        return jobRepository.findAllByProjectIdOrderByCreatedAtDesc(projectId)
                .stream()
                .map(OptimizationJobResponse::fromEntity)
                .toList();
    }

    private Project getProjectOrThrow(UUID projectId) {
        return projectRepository.findById(projectId)
                .orElseThrow(() -> new ProjectNotFoundException(projectId));
    }

    private Map<String, Object> buildWtgGeoJson(List<WtgLocation> wtgs) {
        List<Map<String, Object>> features = new ArrayList<>();
        for (WtgLocation wtg : wtgs) {
            Map<String, Object> feature = new LinkedHashMap<>();
            feature.put("type", "Feature");
            feature.put("id", wtg.getExternalId());

            Map<String, Object> geometry = new LinkedHashMap<>();
            geometry.put("type", "Point");
            geometry.put("coordinates", List.of(wtg.getLocation().getX(), wtg.getLocation().getY()));
            feature.put("geometry", geometry);

            Map<String, Object> properties = new LinkedHashMap<>();
            properties.put("id", wtg.getExternalId());
            properties.put("capacity_mw", wtg.getCapacityMw() != null ? wtg.getCapacityMw().doubleValue() : 3.0);
            feature.put("properties", properties);

            features.add(feature);
        }

        Map<String, Object> featureCollection = new LinkedHashMap<>();
        featureCollection.put("type", "FeatureCollection");
        featureCollection.put("features", features);
        return featureCollection;
    }

    private Map<String, Object> buildSubstationGeoJson(List<Substation> substations, List<WtgLocation> wtgs) {
        List<Map<String, Object>> features = new ArrayList<>();
        Substation primary = selectPrimarySubstation(substations, wtgs);
        List<Substation> targetList = primary != null ? List.of(primary) : List.of();

        for (Substation sub : targetList) {
            Map<String, Object> feature = new LinkedHashMap<>();
            feature.put("type", "Feature");
            feature.put("id", sub.getExternalId());

            Map<String, Object> geometry = new LinkedHashMap<>();
            geometry.put("type", "Point");
            geometry.put("coordinates", List.of(sub.getLocation().getX(), sub.getLocation().getY()));
            feature.put("geometry", geometry);

            Map<String, Object> properties = new LinkedHashMap<>();
            properties.put("id", sub.getExternalId());
            if (sub.getCapacityMw() != null) {
                properties.put("capacity_mw", sub.getCapacityMw().doubleValue());
            }
            feature.put("properties", properties);

            features.add(feature);
        }

        Map<String, Object> featureCollection = new LinkedHashMap<>();
        featureCollection.put("type", "FeatureCollection");
        featureCollection.put("features", features);
        return featureCollection;
    }

    /**
     * Builds one avoidance FeatureCollection from the project's already-reviewed and persisted
     * reference lines, cadastral parcels, and restricted areas, following the routing-treatment
     * policy from docs/whats-next.md §2.2: roads/HT-lines/watercourses and land parcels are soft
     * (crossable, penalized) constraints; restricted/no-go areas are hard exclusions. Returns null
     * when the project has no such features, so the request omits avoidance_geojson entirely
     * rather than sending an empty collection.
     */
    private Map<String, Object> buildAvoidanceGeoJson(UUID projectId, ScenarioProfile profile) {
        List<Map<String, Object>> features = new ArrayList<>();

        for (ReferenceLine line : referenceLineRepository.findAllByProjectIdOrderByExternalIdAsc(projectId)) {
            if (!line.getLineType().isCrossingConstraint() || line.getPath() == null) {
                continue; // EVACUATION_ROUTE, MEASUREMENT and UNKNOWN carry no avoidance meaning
            }
            List<List<Double>> coords = new ArrayList<>();
            for (Coordinate c : line.getPath().getCoordinates()) {
                coords.add(List.of(c.getX(), c.getY()));
            }
            Map<String, Object> geometry = new LinkedHashMap<>();
            geometry.put("type", "LineString");
            geometry.put("coordinates", coords);

            String constraintType = lineConstraintType(line.getLineType());
            Double importedCost = line.getCrossingCost() != null ? line.getCrossingCost().doubleValue() : null;

            Map<String, Object> properties = new LinkedHashMap<>();
            properties.put("constraint_id", "line-" + line.getId());
            properties.put("constraint_type", constraintType);
            properties.put("routing_mode", "soft");
            // Always explicit: the scenario multiplier has to be applied to a known base, and
            // sending Python's own default at a 1.0 multiplier keeps Balanced byte-identical.
            properties.put("cost_weight", "watercourse".equals(constraintType)
                    ? profile.watercourseCost(importedCost)
                    : profile.crossingCost(importedCost));

            features.add(avoidanceFeature("line-" + line.getId(), geometry, properties));
        }

        for (CadastralParcel parcel : parcelRepository.findAllByProjectIdOrderByParcelIdAsc(projectId)) {
            if (parcel.getGeometry() == null) {
                continue;
            }
            Map<String, Object> properties = new LinkedHashMap<>();
            properties.put("constraint_id", "parcel-" + parcel.getId());
            properties.put("constraint_type", "parcel");
            properties.put("routing_mode", "soft");
            properties.put("cost_weight", profile.parcelCost());

            features.add(avoidanceFeature("parcel-" + parcel.getId(), polygonGeoJson(parcel.getGeometry()), properties));
        }

        for (RestrictedArea area : restrictedAreaRepository.findAllByProjectIdOrderByNameAsc(projectId)) {
            if (area.getGeometry() == null) {
                continue;
            }
            Map<String, Object> properties = new LinkedHashMap<>();
            properties.put("constraint_id", "restricted-" + area.getId());
            properties.put("constraint_type", "restricted_area");
            properties.put("routing_mode", "hard");
            // Hard exclusions must not carry cost_weight (Python rejects it), so the environmental
            // scenario expresses its preference as extra routing clearance instead.
            properties.put("buffer_m", profile.restrictedBufferMeters(
                    area.getBufferMeters() != null ? area.getBufferMeters().doubleValue() : null));

            features.add(avoidanceFeature("restricted-" + area.getId(), polygonGeoJson(area.getGeometry()), properties));
        }

        if (features.isEmpty()) {
            return null;
        }
        Map<String, Object> featureCollection = new LinkedHashMap<>();
        featureCollection.put("type", "FeatureCollection");
        featureCollection.put("features", features);
        return featureCollection;
    }

    private static Map<String, Object> avoidanceFeature(String id, Map<String, Object> geometry, Map<String, Object> properties) {
        Map<String, Object> feature = new LinkedHashMap<>();
        feature.put("type", "Feature");
        feature.put("id", id);
        feature.put("geometry", geometry);
        feature.put("properties", properties);
        return feature;
    }

    private static String voltage(CreateOptimizationJobRequest req) {
        return req.voltageKv() != null ? req.voltageKv().toPlainString() : "33";
    }

    private static String lineConstraintType(LineType lineType) {
        return switch (lineType) {
            case ROAD -> "road";
            case HT_LINE -> "ht_line";
            case WATERCOURSE -> "watercourse";
            case EVACUATION_ROUTE, MEASUREMENT, UNKNOWN -> "road";
        };
    }

    private static Map<String, Object> polygonGeoJson(Polygon polygon) {
        List<List<Double>> exterior = new ArrayList<>();
        for (Coordinate c : polygon.getExteriorRing().getCoordinates()) {
            exterior.add(List.of(c.getX(), c.getY()));
        }
        List<List<List<Double>>> rings = new ArrayList<>();
        rings.add(exterior);
        for (int i = 0; i < polygon.getNumInteriorRing(); i++) {
            List<List<Double>> interior = new ArrayList<>();
            for (Coordinate c : polygon.getInteriorRingN(i).getCoordinates()) {
                interior.add(List.of(c.getX(), c.getY()));
            }
            rings.add(interior);
        }
        Map<String, Object> geometry = new LinkedHashMap<>();
        geometry.put("type", "Polygon");
        geometry.put("coordinates", rings);
        return geometry;
    }

    /**
     * Combines the legacy metrics with the rich candidate comparison, recommendation reasoning,
     * and electrical/network/pole summaries Python already computes but the old integration
     * silently discarded, so the UI can answer "why this route" instead of showing a bare line.
     */
    private static Map<String, Object> buildResultSummary(PythonOptimisationResponse pythonResp) {
        Map<String, Object> summary = new LinkedHashMap<>();
        summary.put("metrics", pythonResp.metrics() != null ? pythonResp.metrics() : Map.of());
        summary.put("workflowStatus", pythonResp.workflowStatus());
        summary.put("candidates", pythonResp.candidates() != null ? pythonResp.candidates() : List.of());
        summary.put("recommendation", pythonResp.recommendation());
        summary.put("failures", pythonResp.failures() != null ? pythonResp.failures() : List.of());

        Map<String, Object> recommendedResult = pythonResp.recommendedResult();
        if (recommendedResult != null) {
            putIfPresent(summary, "networkSummary", recommendedResult.get("network_summary"));
            putIfPresent(summary, "electricalSummary", recommendedResult.get("electrical_summary"));
            putIfPresent(summary, "poleSummary", recommendedResult.get("pole_summary"));
            putIfPresent(summary, "spatialConstraintSummary", recommendedResult.get("spatial_constraint_summary"));
        }
        return summary;
    }

    private static void putIfPresent(Map<String, Object> target, String key, Object value) {
        if (value != null) {
            target.put(key, value);
        }
    }

    /** Turns Python's structured rejection into a message an engineer can act on. */
    private static String describeFailure(PythonOptimisationResponse pythonResp) {
        if (pythonResp.recommendation() != null) {
            Object reasons = pythonResp.recommendation().get("reasons");
            List<String> reasonList = asStringList(reasons);
            if (!reasonList.isEmpty()) {
                return "No feasible route: " + String.join("; ", reasonList);
            }
        }
        if (pythonResp.candidates() != null && !pythonResp.candidates().isEmpty()) {
            List<String> reasons = pythonResp.candidates().stream()
                    .flatMap(candidate -> asStringList(candidate.get("disqualifications")).stream())
                    .distinct()
                    .toList();
            if (!reasons.isEmpty()) {
                return "No electrically or spatially feasible candidate: " + String.join("; ", reasons);
            }
        }
        if (pythonResp.failures() != null && !pythonResp.failures().isEmpty()) {
            Object message = pythonResp.failures().get(0).get("message");
            if (message != null) {
                return "Optimization failed: " + message;
            }
        }
        return "Python optimization failed with status: " + pythonResp.status();
    }

    private static List<String> asStringList(Object value) {
        if (value instanceof List<?> list) {
            return list.stream().map(String::valueOf).toList();
        }
        return List.of();
    }

    /**
     * Picks the substation the feeders should connect to when a project has more than one.
     *
     * <p>Prefers the highest-capacity substation when at least one reports a positive capacity.
     * Survey KMZ files typically carry no capacity metadata at all, in which case every substation
     * ties at zero; falling back to list order in that case previously picked an arbitrary (often
     * distant) substation, producing an infeasible or absurdly long route. Instead, when capacity
     * gives no signal, pick whichever substation sits closest to the WTG cluster.
     */
    private static Substation selectPrimarySubstation(List<Substation> substations, List<WtgLocation> wtgs) {
        if (substations.isEmpty()) {
            return null;
        }
        if (substations.size() == 1) {
            return substations.get(0);
        }

        boolean anyCapacityKnown = substations.stream()
                .anyMatch(s -> s.getCapacityMw() != null && s.getCapacityMw().signum() > 0);
        if (anyCapacityKnown) {
            return substations.stream()
                    .max(Comparator.comparing(s -> s.getCapacityMw() != null ? s.getCapacityMw() : BigDecimal.ZERO))
                    .orElse(substations.get(0));
        }

        if (wtgs.isEmpty()) {
            return substations.get(0);
        }
        double centroidLon = wtgs.stream().mapToDouble(w -> w.getLocation().getX()).average().orElse(0);
        double centroidLat = wtgs.stream().mapToDouble(w -> w.getLocation().getY()).average().orElse(0);

        return substations.stream()
                .min(Comparator.comparingDouble(s -> haversineMeters(
                        centroidLon, centroidLat, s.getLocation().getX(), s.getLocation().getY())))
                .orElse(substations.get(0));
    }

    private static double haversineMeters(double lon1, double lat1, double lon2, double lat2) {
        double earthRadiusM = 6_371_000.0;
        double dLat = Math.toRadians(lat2 - lat1);
        double dLon = Math.toRadians(lon2 - lon1);
        double a = Math.sin(dLat / 2) * Math.sin(dLat / 2)
                + Math.cos(Math.toRadians(lat1)) * Math.cos(Math.toRadians(lat2))
                * Math.sin(dLon / 2) * Math.sin(dLon / 2);
        double c = 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1 - a));
        return earthRadiusM * c;
    }
}
