package com.power.surge.controller;

import com.power.surge.dto.report.EngineeringBomReportResponse;
import com.power.surge.service.ReportService;
import org.springframework.http.HttpHeaders;
import org.springframework.http.MediaType;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

import java.util.UUID;

@RestController
@RequestMapping("/api/v1/projects/{projectId}/reports")
public class ReportController {

    private final ReportService reportService;

    public ReportController(ReportService reportService) {
        this.reportService = reportService;
    }

    @GetMapping("/bom")
    public EngineeringBomReportResponse getLatestBomReport(@PathVariable UUID projectId) {
        return reportService.generateBomReport(projectId, null);
    }

    @GetMapping("/jobs/{jobId}/bom")
    public EngineeringBomReportResponse getJobBomReport(
            @PathVariable UUID projectId,
            @PathVariable UUID jobId
    ) {
        return reportService.generateBomReport(projectId, jobId);
    }

    @GetMapping(value = "/bom/csv", produces = "text/csv")
    public ResponseEntity<String> downloadLatestBomCsv(@PathVariable UUID projectId) {
        String csv = reportService.generateBomCsv(projectId, null);
        return ResponseEntity.ok()
                .header(HttpHeaders.CONTENT_DISPOSITION, "attachment; filename=\"project-" + projectId + "-bom.csv\"")
                .contentType(MediaType.parseMediaType("text/csv"))
                .body(csv);
    }

    @GetMapping(value = "/jobs/{jobId}/bom/csv", produces = "text/csv")
    public ResponseEntity<String> downloadJobBomCsv(
            @PathVariable UUID projectId,
            @PathVariable UUID jobId
    ) {
        String csv = reportService.generateBomCsv(projectId, jobId);
        return ResponseEntity.ok()
                .header(HttpHeaders.CONTENT_DISPOSITION, "attachment; filename=\"job-" + jobId + "-bom.csv\"")
                .contentType(MediaType.parseMediaType("text/csv"))
                .body(csv);
    }
}
