package com.power.surge.service;

import com.power.surge.domain.CadastralParcel;
import com.power.surge.domain.GeneratedRoute;
import com.power.surge.domain.JobStatus;
import com.power.surge.domain.OptimizationJob;
import com.power.surge.domain.Project;
import com.power.surge.dto.report.EngineeringBomReportResponse;
import com.power.surge.dto.report.FeederBomSummary;
import com.power.surge.dto.report.ParcelImpactSummary;
import com.power.surge.repository.CadastralParcelRepository;
import com.power.surge.repository.GeneratedRouteRepository;
import com.power.surge.repository.OptimizationJobRepository;
import com.power.surge.repository.ProjectRepository;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.math.BigDecimal;
import java.math.RoundingMode;
import java.time.Instant;
import java.util.ArrayList;
import java.util.List;
import java.util.UUID;

@Service
@Transactional(readOnly = true)
public class ReportService {

    private final ProjectRepository projectRepository;
    private final OptimizationJobRepository jobRepository;
    private final GeneratedRouteRepository routeRepository;
    private final CadastralParcelRepository parcelRepository;

    public ReportService(
            ProjectRepository projectRepository,
            OptimizationJobRepository jobRepository,
            GeneratedRouteRepository routeRepository,
            CadastralParcelRepository parcelRepository
    ) {
        this.projectRepository = projectRepository;
        this.jobRepository = jobRepository;
        this.routeRepository = routeRepository;
        this.parcelRepository = parcelRepository;
    }

    public EngineeringBomReportResponse generateBomReport(UUID projectId, UUID jobId) {
        Project project = getProjectOrThrow(projectId);
        OptimizationJob job = resolveJob(projectId, jobId);

        List<GeneratedRoute> routes = routeRepository.findAllByJobIdOrderByFeederNameAsc(job.getId());
        List<CadastralParcel> parcels = parcelRepository.findAllByProjectIdOrderByParcelIdAsc(projectId);

        List<FeederBomSummary> feederSummaries = new ArrayList<>();
        BigDecimal totalLength = BigDecimal.ZERO;
        BigDecimal totalCost = BigDecimal.ZERO;
        BigDecimal totalLosses = BigDecimal.ZERO;
        int totalPoles = 0;

        for (GeneratedRoute r : routes) {
            feederSummaries.add(new FeederBomSummary(
                    r.getFeederName(),
                    r.getTotalLengthMeters(),
                    r.getPoleCount(),
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
            if (r.getPoleCount() != null) {
                totalPoles += r.getPoleCount();
            }
        }

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
