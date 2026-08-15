package com.power.surge.controller;

import com.power.surge.dto.report.EngineeringBomReportResponse;
import com.power.surge.dto.report.FeederBomSummary;
import com.power.surge.repository.CadastralParcelRepository;
import com.power.surge.repository.GeneratedRouteRepository;
import com.power.surge.repository.OptimizationJobRepository;
import com.power.surge.repository.ProjectRepository;
import com.power.surge.service.ReportService;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.autoconfigure.data.jpa.JpaRepositoriesAutoConfiguration;
import org.springframework.boot.test.autoconfigure.web.servlet.WebMvcTest;
import org.springframework.boot.test.mock.mockito.MockBean;
import org.springframework.http.MediaType;
import org.springframework.test.context.ActiveProfiles;
import org.springframework.test.web.servlet.MockMvc;

import java.math.BigDecimal;
import java.time.Instant;
import java.util.List;
import java.util.UUID;

import static org.mockito.ArgumentMatchers.eq;
import static org.mockito.Mockito.when;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.content;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.header;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

import org.springframework.boot.test.autoconfigure.web.servlet.AutoConfigureMockMvc;
import com.power.surge.security.JwtTokenProvider;

@WebMvcTest(controllers = ReportController.class, excludeAutoConfiguration = { JpaRepositoriesAutoConfiguration.class })
@AutoConfigureMockMvc(addFilters = false)
@ActiveProfiles("test")
class ReportControllerTest {

    @Autowired
    private MockMvc mockMvc;

    @MockBean
    private JwtTokenProvider jwtTokenProvider;

    // The authentication filter now resolves the account behind the token, so every slice that
    // builds the security chain needs the repository it reads.
    @MockBean
    private com.power.surge.repository.UserRepository userRepository;

    @MockBean
    private com.power.surge.service.AuthService authService;

    @MockBean
    private ReportService reportService;

    @MockBean
    private com.power.surge.service.PdfReportService pdfReportService;

    @MockBean
    private ProjectRepository projectRepository;

    @MockBean
    private OptimizationJobRepository jobRepository;

    @MockBean
    private GeneratedRouteRepository routeRepository;

    @MockBean
    private CadastralParcelRepository parcelRepository;

    @Test
    void getsLatestBomReport() throws Exception {
        UUID projectId = UUID.randomUUID();
        UUID jobId = UUID.randomUUID();

        FeederBomSummary feeder = new FeederBomSummary("Feeder-01", new BigDecimal("2500.00"), 15, new BigDecimal("150000.00"), new BigDecimal("12.50"));

        EngineeringBomReportResponse response = new EngineeringBomReportResponse(
                projectId,
                "Gujarat Wind Farm",
                jobId,
                1,
                new BigDecimal("2500.00"),
                15,
                new BigDecimal("150000.00"),
                new BigDecimal("12.50"),
                List.of(feeder),
                List.of(),
                Instant.now()
        );

        when(reportService.generateBomReport(projectId, null)).thenReturn(response);

        mockMvc.perform(get("/api/v1/projects/{projectId}/reports/bom", projectId))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.projectName").value("Gujarat Wind Farm"))
                .andExpect(jsonPath("$.totalFeeders").value(1))
                .andExpect(jsonPath("$.feederSummaries[0].feederName").value("Feeder-01"));
    }

    @Test
    void downloadsLatestBomCsv() throws Exception {
        UUID projectId = UUID.randomUUID();
        String csvContent = "SURGE Engineering Bill of Materials (BOM) Report\nProject Name,Gujarat Wind Farm\n";

        when(reportService.generateBomCsv(projectId, null)).thenReturn(csvContent);

        mockMvc.perform(get("/api/v1/projects/{projectId}/reports/bom/csv", projectId))
                .andExpect(status().isOk())
                .andExpect(header().string("Content-Type", MediaType.parseMediaType("text/csv").toString()))
                .andExpect(content().string(csvContent));
    }

    @Test
    void getsScenarioComparison() throws Exception {
        UUID projectId = UUID.randomUUID();

        com.power.surge.dto.report.ScenarioComparisonResponse response = new com.power.surge.dto.report.ScenarioComparisonResponse(
                projectId,
                List.of(new com.power.surge.dto.report.ScenarioSummaryItem(
                        "Balanced", UUID.randomUUID(), com.power.surge.domain.JobStatus.COMPLETED,
                        8450.0, 56, 676000.0, 42.5, 36000.0, 0.0, 0.0
                ))
        );

        when(reportService.getScenarioComparison(projectId)).thenReturn(response);

        mockMvc.perform(get("/api/v1/projects/{projectId}/reports/scenarios/compare", projectId))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.projectId").value(projectId.toString()))
                .andExpect(jsonPath("$.scenarios[0].scenarioName").value("Balanced"));
    }

    @Test
    void downloadsExecutivePdfReport() throws Exception {
        UUID projectId = UUID.randomUUID();
        byte[] pdfBytes = "%PDF-1.4 dummy pdf content".getBytes();

        when(pdfReportService.generateExecutivePdfReport(projectId)).thenReturn(pdfBytes);

        mockMvc.perform(get("/api/v1/projects/{projectId}/reports/pdf", projectId))
                .andExpect(status().isOk())
                .andExpect(header().string("Content-Type", MediaType.APPLICATION_PDF_VALUE))
                .andExpect(content().bytes(pdfBytes));
    }
}
