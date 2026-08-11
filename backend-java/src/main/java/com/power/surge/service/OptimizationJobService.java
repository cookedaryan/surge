package com.power.surge.service;

import com.fasterxml.jackson.databind.ObjectMapper;
import com.power.surge.client.PythonOptimizationClient;
import com.power.surge.domain.OptimizationJob;
import com.power.surge.domain.Project;
import com.power.surge.domain.Substation;
import com.power.surge.domain.WtgLocation;
import com.power.surge.dto.client.python.PythonOptimisationRequest;
import com.power.surge.dto.client.python.PythonOptimisationResponse;
import com.power.surge.dto.job.CreateOptimizationJobRequest;
import com.power.surge.dto.job.OptimizationJobResponse;
import com.power.surge.repository.GeneratedRouteRepository;
import com.power.surge.repository.OptimizationJobRepository;
import com.power.surge.repository.ProjectRepository;
import com.power.surge.repository.SubstationRepository;
import com.power.surge.repository.WtgLocationRepository;
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
public class OptimizationJobService {

    private static final Logger log = LoggerFactory.getLogger(OptimizationJobService.class);

    private final ProjectRepository projectRepository;
    private final OptimizationJobRepository jobRepository;
    private final GeneratedRouteRepository routeRepository;
    private final WtgLocationRepository wtgLocationRepository;
    private final SubstationRepository substationRepository;
    private final RouteService routeService;
    private final PythonOptimizationClient pythonClient;
    private final ObjectMapper objectMapper;
    private final SseProgressService sseProgressService;

    public OptimizationJobService(
            ProjectRepository projectRepository,
            OptimizationJobRepository jobRepository,
            GeneratedRouteRepository routeRepository,
            WtgLocationRepository wtgLocationRepository,
            SubstationRepository substationRepository,
            RouteService routeService,
            PythonOptimizationClient pythonClient,
            ObjectMapper objectMapper,
            SseProgressService sseProgressService
    ) {
        this.projectRepository = projectRepository;
        this.jobRepository = jobRepository;
        this.routeRepository = routeRepository;
        this.wtgLocationRepository = wtgLocationRepository;
        this.substationRepository = substationRepository;
        this.routeService = routeService;
        this.pythonClient = pythonClient;
        this.objectMapper = objectMapper;
        this.sseProgressService = sseProgressService;
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
            Map<String, Object> subGeoJson = buildSubstationGeoJson(substations);

            String scenario = req.scenario() != null ? req.scenario() : "Balanced";

            Map<String, Object> electricalParams = new LinkedHashMap<>();
            electricalParams.put("feeder_capacity_mw", req.feederCapacityMw() != null ? req.feederCapacityMw().doubleValue() : 20.0);
            electricalParams.put("max_voltage_drop_pct", req.maxVoltageDropPct() != null ? req.maxVoltageDropPct().doubleValue() : 5.0);
            electricalParams.put("row_width_m", req.rowWidthM() != null ? req.rowWidthM().doubleValue() : 18.0);

            PythonOptimisationRequest pythonReq = new PythonOptimisationRequest(
                    "job-" + job.getId(),
                    projectId.toString(),
                    scenario,
                    wtgGeoJson,
                    subGeoJson,
                    electricalParams
            );

            PythonOptimisationResponse pythonResp = pythonClient.runOptimization(pythonReq);

            sseProgressService.emitProgress(job.getId(), 70, "Processing radial feeder topology and route outputs", com.power.surge.domain.JobStatus.RUNNING);
            String summaryJson = objectMapper.writeValueAsString(pythonResp.metrics() != null ? pythonResp.metrics() : Map.of());

            if ("success".equalsIgnoreCase(pythonResp.status())) {
                if (pythonResp.feederRoutesGeojson() != null && !pythonResp.feederRoutesGeojson().isEmpty()) {
                    sseProgressService.emitProgress(job.getId(), 85, "Saving route geometries and pole locations to PostGIS", com.power.surge.domain.JobStatus.RUNNING);
                    routeService.saveRoutesFromGeoJson(job.getId(), pythonResp.feederRoutesGeojson());
                }
                job.markCompleted(summaryJson);
                sseProgressService.completeProgress(job.getId(), "Optimization job completed successfully!", true);
            } else {
                String errMsg = "Python optimization failed with status: " + pythonResp.status();
                job.markFailed(errMsg);
                sseProgressService.completeProgress(job.getId(), errMsg, false);
            }

        } catch (Exception e) {
            log.error("Failed to run optimization job {}", job.getId(), e);
            String errMsg = "Error dispatching optimization job: " + e.getMessage();
            job.markFailed(errMsg);
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

    private Map<String, Object> buildSubstationGeoJson(List<Substation> substations) {
        List<Map<String, Object>> features = new ArrayList<>();
        for (Substation sub : substations) {
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
}
