package com.power.surge.service;

import com.power.surge.domain.CadastralParcel;
import com.power.surge.domain.GeneratedPole;
import com.power.surge.domain.GeneratedRoute;
import com.power.surge.domain.JobStatus;
import com.power.surge.domain.OptimizationJob;
import com.power.surge.domain.Project;
import com.power.surge.dto.report.EngineeringBomReportResponse;
import com.power.surge.dto.report.FeederBomSummary;
import com.power.surge.dto.report.ParcelImpactSummary;
import com.power.surge.repository.CadastralParcelRepository;
import com.power.surge.repository.GeneratedPoleRepository;
import com.power.surge.repository.GeneratedRouteRepository;
import com.power.surge.repository.OptimizationJobRepository;
import com.power.surge.repository.ProjectRepository;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.math.BigDecimal;
import java.math.RoundingMode;
import java.time.Instant;
import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Objects;
import java.util.Map;
import java.util.UUID;

@Service
@Transactional(readOnly = true)
public class ReportService {

    private final ProjectRepository projectRepository;
    private final OptimizationJobRepository jobRepository;
    private final GeneratedRouteRepository routeRepository;
    private final GeneratedPoleRepository poleRepository;
    private final CadastralParcelRepository parcelRepository;
    private final AuditLogService auditLogService;

    public ReportService(
            ProjectRepository projectRepository,
            OptimizationJobRepository jobRepository,
            GeneratedRouteRepository routeRepository,
            GeneratedPoleRepository poleRepository,
            CadastralParcelRepository parcelRepository,
            AuditLogService auditLogService
    ) {
        this.projectRepository = projectRepository;
        this.jobRepository = jobRepository;
        this.routeRepository = routeRepository;
        this.poleRepository = poleRepository;
        this.parcelRepository = parcelRepository;
        this.auditLogService = auditLogService;
    }

    public EngineeringBomReportResponse generateBomReport(UUID projectId, UUID jobId) {
        Project project = getProjectOrThrow(projectId);
        OptimizationJob job = resolveJob(projectId, jobId);

        List<GeneratedRoute> routes = routeRepository.findAllByJobIdOrderByFeederNameAsc(job.getId());
        List<CadastralParcel> parcels = parcelRepository.findAllByProjectIdOrderByParcelIdAsc(projectId);

        List<GeneratedPole> poles = poleRepository.findAllByJobIdOrderByPoleIdentifierAsc(job.getId());
        Map<String, Long> poleCountBySegment = poleCountBySegmentId(poles);

        List<FeederBomSummary> feederSummaries = new ArrayList<>();
        BigDecimal totalLength = BigDecimal.ZERO;
        BigDecimal totalCost = BigDecimal.ZERO;
        BigDecimal totalLosses = BigDecimal.ZERO;

        for (GeneratedRoute r : routes) {
            // GeneratedRoute.poleCount is only ever a /150m fallback estimate (routes are persisted
            // before real pole placement runs, and can predate it entirely for older jobs). Prefer
            // the real per-segment count so this matches what the map popup shows for this route.
            Long realCount = r.getSegmentId() != null ? poleCountBySegment.get(r.getSegmentId()) : null;
            int rowPoleCount = realCount != null ? realCount.intValue() : (r.getPoleCount() != null ? r.getPoleCount() : 0);

            feederSummaries.add(new FeederBomSummary(
                    r.getFeederName(),
                    r.getTotalLengthMeters(),
                    rowPoleCount,
                    r.getTotalCost(),
                    r.getElectricalLossesKw()
            ));

            if (r.getTotalLengthMeters() != null) {
                totalLength = totalLength.add(r.getTotalLengthMeters());
            }
            if (r.getTotalCost() != null) {
                totalCost = totalCost.add(r.getTotalCost());
            }
            if (r.getElectricalLossesKw() != null) {
                totalLosses = totalLosses.add(r.getElectricalLossesKw());
            }
        }

        // The network total counts each physical pole once, even where a junction pole is shared
        // by two segments and so appears in both of their row counts above.
        int totalPoles = !poles.isEmpty() ? poles.size() : feederSummaries.stream().mapToInt(FeederBomSummary::poleCount).sum();

        List<ParcelImpactSummary> parcelSummaries = new ArrayList<>();
        for (CadastralParcel p : parcels) {
            Double affectedArea = p.getGeometry() != null ? p.getGeometry().getArea() * 111000.0 * 111000.0 * 0.001 : 0.0;
            BigDecimal costRate = p.getAcquisitionCostPerM2() != null ? p.getAcquisitionCostPerM2() : BigDecimal.ZERO;
            BigDecimal estimatedComp = costRate.multiply(BigDecimal.valueOf(affectedArea)).setScale(2, RoundingMode.HALF_UP);

            parcelSummaries.add(new ParcelImpactSummary(
                    p.getParcelId(),
                    p.getOwnerName(),
                    p.getAcquisitionCostPerM2(),
                    affectedArea,
                    estimatedComp
            ));
        }

        return new EngineeringBomReportResponse(
                projectId,
                project.getName(),
                job.getId(),
                routes.size(),
                totalLength.setScale(2, RoundingMode.HALF_UP),
                totalPoles,
                totalCost.setScale(2, RoundingMode.HALF_UP),
                totalLosses.setScale(2, RoundingMode.HALF_UP),
                feederSummaries,
                parcelSummaries,
                Instant.now()
        );
    }

    public String generateBomCsv(UUID projectId, UUID jobId) {
        EngineeringBomReportResponse report = generateBomReport(projectId, jobId);

        // Audited here rather than in generateBomReport: that method also backs the always-visible
        // BOM panel, so auditing it would bury real actions under a stream of page renders. Taking
        // data out of the system is the event worth recording.
        auditLogService.record("REPORT_EXPORTED", "PROJECT", projectId.toString(),
                "Exported BOM CSV for project '" + report.projectName() + "'"
                        + (report.jobId() != null ? " (job " + report.jobId() + ")" : ""));

        StringBuilder csv = new StringBuilder();
        csv.append("SURGE Engineering Bill of Materials (BOM) Report\n");
        csv.append("Project Name,").append(escapeCsv(report.projectName())).append("\n");
        csv.append("Project ID,").append(report.projectId()).append("\n");
        csv.append("Job ID,").append(report.jobId()).append("\n");
        csv.append("Generated At,").append(report.generatedAt()).append("\n\n");

        csv.append("--- FEEDER NETWORK SCHEDULE ---\n");
        csv.append("Feeder Name,Length (m),Pole Count,Total Cost ($),Electrical Losses (kW)\n");

        for (FeederBomSummary f : report.feederSummaries()) {
            csv.append(escapeCsv(f.feederName())).append(",")
                    .append(f.lengthMeters()).append(",")
                    .append(f.poleCount()).append(",")
                    .append(f.totalCost() != null ? f.totalCost() : 0.0).append(",")
                    .append(f.electricalLossesKw() != null ? f.electricalLossesKw() : 0.0).append("\n");
        }

        csv.append("\nTOTALS,")
                .append(report.totalNetworkLengthMeters()).append(",")
                .append(report.totalPoles()).append(",")
                .append(report.totalEstimatedCost()).append(",")
                .append(report.totalElectricalLossesKw()).append("\n\n");

        csv.append("--- CADASTRAL PARCEL IMPACT & COMPENSATION ---\n");
        csv.append("Parcel ID,Owner Name,Rate ($/m2),Affected Area (m2),Estimated Compensation ($)\n");

        for (ParcelImpactSummary p : report.parcelImpactSummaries()) {
            csv.append(escapeCsv(p.parcelId())).append(",")
                    .append(escapeCsv(p.ownerName() != null ? p.ownerName() : "")).append(",")
                    .append(p.acquisitionCostPerM2() != null ? p.acquisitionCostPerM2() : 0.0).append(",")
                    .append(String.format("%.2f", p.affectedAreaM2())).append(",")
                    .append(p.estimatedCompensationCost()).append("\n");
        }

        return csv.toString();
    }

    private static final List<String> SCENARIO_NAMES =
            List.of("Balanced", "Minimum Cost", "Minimum Land Impact", "Minimum Environmental Impact");

    /**
     * Compares actual completed jobs per scenario for this project. A scenario the user hasn't
     * run yet is simply omitted rather than filled in with an invented number — the previous
     * implementation returned the same four hardcoded length/pole/cost figures for every project
     * regardless of what was actually run.
     */
    public com.power.surge.dto.report.ScenarioComparisonResponse getScenarioComparison(UUID projectId) {
        getProjectOrThrow(projectId);
        List<OptimizationJob> jobs = jobRepository.findAllByProjectIdOrderByCreatedAtDesc(projectId);

        // Prefer the most recent completed Balanced run as the delta baseline; fall back to
        // whatever scenario was run most recently if Balanced hasn't been, so deltas still have
        // a reference point instead of silently disappearing.
        OptimizationJob baseJob = jobs.stream()
                .filter(j -> j.getStatus() == JobStatus.COMPLETED && "Balanced".equalsIgnoreCase(j.getScenario()))
                .findFirst()
                .orElseGet(() -> jobs.stream().filter(j -> j.getStatus() == JobStatus.COMPLETED).findFirst().orElse(null));

        Double baseCost = null;
        Double baseLosses = null;
        if (baseJob != null) {
            EngineeringBomReportResponse baseReport = generateBomReport(projectId, baseJob.getId());
            baseCost = baseReport.totalEstimatedCost() != null ? baseReport.totalEstimatedCost().doubleValue() : null;
            baseLosses = baseReport.totalElectricalLossesKw() != null ? baseReport.totalElectricalLossesKw().doubleValue() : null;
        }

        List<com.power.surge.dto.report.ScenarioSummaryItem> items = new ArrayList<>();
        for (String scName : SCENARIO_NAMES) {
            OptimizationJob scJob = jobs.stream()
                    .filter(j -> j.getStatus() == JobStatus.COMPLETED && scName.equalsIgnoreCase(j.getScenario()))
                    .findFirst()
                    .orElse(null);
            if (scJob == null) {
                continue;
            }

            EngineeringBomReportResponse report = generateBomReport(projectId, scJob.getId());
            Double length = report.totalNetworkLengthMeters() != null ? report.totalNetworkLengthMeters().doubleValue() : null;
            Double cost = report.totalEstimatedCost() != null ? report.totalEstimatedCost().doubleValue() : null;
            Double losses = report.totalElectricalLossesKw() != null ? report.totalElectricalLossesKw().doubleValue() : null;
            double landCost = report.parcelImpactSummaries().stream()
                    .map(ParcelImpactSummary::estimatedCompensationCost)
                    .filter(Objects::nonNull)
                    .mapToDouble(BigDecimal::doubleValue)
                    .sum();

            items.add(new com.power.surge.dto.report.ScenarioSummaryItem(
                    scName,
                    scJob.getId(),
                    scJob.getStatus(),
                    length,
                    report.totalPoles(),
                    cost,
                    losses,
                    landCost,
                    percentDelta(cost, baseCost),
                    percentDelta(losses, baseLosses)
            ));
        }

        return new com.power.surge.dto.report.ScenarioComparisonResponse(projectId, items);
    }

    private static Double percentDelta(Double value, Double base) {
        if (value == null || base == null || base == 0) {
            return null;
        }
        return Math.round(((value - base) / base) * 1000.0) / 10.0;
    }

    /**
     * Counts real placed poles per segment_id. A junction pole can carry more than one
     * segment_id (it's shared between the two edges that meet there), so it's counted once
     * toward each — matching what a rider would actually see standing at each individual segment.
     */
    private static Map<String, Long> poleCountBySegmentId(List<GeneratedPole> poles) {
        Map<String, Long> counts = new LinkedHashMap<>();
        for (GeneratedPole pole : poles) {
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

    private Project getProjectOrThrow(UUID projectId) {
        return projectRepository.findById(projectId)
                .orElseThrow(() -> new ProjectNotFoundException(projectId));
    }

    private OptimizationJob resolveJob(UUID projectId, UUID jobId) {
        if (jobId != null) {
            OptimizationJob job = jobRepository.findById(jobId)
                    .orElseThrow(() -> new IllegalArgumentException("Optimization job not found: " + jobId));
            if (job.getProject().getId() != null && !job.getProject().getId().equals(projectId)) {
                throw new IllegalArgumentException("Job " + jobId + " does not belong to project " + projectId);
            }
            return job;
        }

        List<OptimizationJob> jobs = jobRepository.findAllByProjectIdOrderByCreatedAtDesc(projectId);
        return jobs.stream()
                .filter(j -> j.getStatus() == JobStatus.COMPLETED)
                .findFirst()
                .orElseGet(() -> jobs.stream().findFirst()
                        .orElseThrow(() -> new IllegalArgumentException("No optimization jobs found for project: " + projectId)));
    }

    private static String escapeCsv(String value) {
        if (value == null) {
            return "";
        }
        if (value.contains(",") || value.contains("\"") || value.contains("\n")) {
            return "\"" + value.replace("\"", "\"\"") + "\"";
        }
        return value;
    }
}
