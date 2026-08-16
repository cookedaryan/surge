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
    private final com.power.surge.service.PdfReportService pdfReportService;

    public ReportController(ReportService reportService, com.power.surge.service.PdfReportService pdfReportService) {
        this.reportService = reportService;
        this.pdfReportService = pdfReportService;
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

    @GetMapping("/scenarios/compare")
    public com.power.surge.dto.report.ScenarioComparisonResponse getScenarioComparison(@PathVariable UUID projectId) {
        return reportService.getScenarioComparison(projectId);
    }

    @GetMapping(value = "/pdf", produces = MediaType.APPLICATION_PDF_VALUE)
    public ResponseEntity<byte[]> downloadExecutivePdfReport(@PathVariable UUID projectId) {
        byte[] pdfBytes = pdfReportService.generateExecutivePdfReport(projectId, null);
        return ResponseEntity.ok()
                .header(HttpHeaders.CONTENT_DISPOSITION, "attachment; filename=\"surge-report-" + projectId + ".pdf\"")
                .contentType(MediaType.APPLICATION_PDF)
                .body(pdfBytes);
    }

    /**
     * The PDF for a specific run. Without this the export always described the most recent job,
     * so exporting while viewing an earlier run produced a report for a different network.
     */
    @GetMapping(value = "/jobs/{jobId}/pdf", produces = MediaType.APPLICATION_PDF_VALUE)
    public ResponseEntity<byte[]> downloadJobPdfReport(
            @PathVariable UUID projectId,
            @PathVariable UUID jobId
    ) {
        byte[] pdfBytes = pdfReportService.generateExecutivePdfReport(projectId, jobId);
        return ResponseEntity.ok()
                .header(HttpHeaders.CONTENT_DISPOSITION, "attachment; filename=\"surge-report-job-" + jobId + ".pdf\"")
                .contentType(MediaType.APPLICATION_PDF)
                .body(pdfBytes);
    }
}
