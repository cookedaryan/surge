package com.power.surge.service;

import com.power.surge.dto.project.ProjectResponse;
import com.power.surge.dto.report.EngineeringBomReportResponse;
import com.power.surge.dto.report.ScenarioComparisonResponse;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.Mock;
import org.mockito.junit.jupiter.MockitoExtension;

import java.math.BigDecimal;
import java.time.Instant;
import java.util.List;
import java.util.UUID;

import static org.assertj.core.api.Assertions.assertThat;
import static org.mockito.ArgumentMatchers.eq;
import static org.mockito.Mockito.when;

@ExtendWith(MockitoExtension.class)
class PdfReportServiceTest {

    @Mock
    private ProjectService projectService;

    @Mock
    private ReportService reportService;

    @Mock
    private AuditLogService auditLogService;

    private PdfReportService pdfReportService;

    @BeforeEach
    void setUp() {
        pdfReportService = new PdfReportService(projectService, reportService, auditLogService);
    }

    @Test
    void generateExecutivePdfReport_success() {
        UUID projectId = UUID.randomUUID();
        ProjectResponse dummyProject = new ProjectResponse(projectId, "Gujarat Wind Farm", "100 MW Evacuation", "EPSG:4326", Instant.now(), Instant.now());
        EngineeringBomReportResponse dummyBom = new EngineeringBomReportResponse(
                projectId, "Gujarat Wind Farm", null,
                new com.power.surge.dto.report.ReportRunParameters(
                        "Balanced", "MULTI_OBJECTIVE_A_STAR", "COMPLETED",
                        new BigDecimal("33"), new BigDecimal("10"), new BigDecimal("150"),
                        new BigDecimal("5"), new BigDecimal("18"), null, null, Instant.now(), Instant.now()),
                2, 5, new BigDecimal("8450.00"), 56,
                java.util.Map.of("tangent", 40, "angle", 16),
                java.util.Map.of("PSC-9M", 56),
                new BigDecimal("676000.00"), new BigDecimal("42.50"),
                new BigDecimal("18"), new BigDecimal("0.00"), new BigDecimal("0.00"),
                List.of(), List.of(), List.of(), List.of(), Instant.now()
        );
        ScenarioComparisonResponse dummyScenarios = new ScenarioComparisonResponse(projectId, List.of());

        when(projectService.getProject(eq(projectId))).thenReturn(dummyProject);
        when(reportService.generateBomReport(eq(projectId), eq(null))).thenReturn(dummyBom);
        when(reportService.getScenarioComparison(eq(projectId))).thenReturn(dummyScenarios);

        byte[] pdfBytes = pdfReportService.generateExecutivePdfReport(projectId, null);

        assertThat(pdfBytes).isNotNull();
        assertThat(pdfBytes.length).isGreaterThan(100);
        // Verify PDF Header Magic Bytes (%PDF-)
        String header = new String(pdfBytes, 0, 5);
        assertThat(header).isEqualTo("%PDF-");
    }
}
