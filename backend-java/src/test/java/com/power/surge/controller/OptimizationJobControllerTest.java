package com.power.surge.controller;

import com.power.surge.domain.JobStatus;
import com.power.surge.dto.job.CreateOptimizationJobRequest;
import com.power.surge.dto.job.OptimizationJobResponse;
import com.power.surge.repository.GeneratedRouteRepository;
import com.power.surge.repository.OptimizationJobRepository;
import com.power.surge.repository.ProjectRepository;
import com.power.surge.service.OptimizationJobService;
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

import static org.mockito.ArgumentMatchers.any;
import static org.mockito.ArgumentMatchers.eq;
import static org.mockito.Mockito.when;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.post;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

import org.springframework.boot.test.autoconfigure.web.servlet.AutoConfigureMockMvc;
import com.power.surge.security.JwtTokenProvider;

@WebMvcTest(controllers = OptimizationJobController.class, excludeAutoConfiguration = { JpaRepositoriesAutoConfiguration.class })
@AutoConfigureMockMvc(addFilters = false)
@ActiveProfiles("test")
class OptimizationJobControllerTest {

    @Autowired
    private MockMvc mockMvc;

    @MockBean
    private JwtTokenProvider jwtTokenProvider;

    @MockBean
    private OptimizationJobService jobService;

    @MockBean
    private ProjectRepository projectRepository;

    @MockBean
    private OptimizationJobRepository jobRepository;

    @MockBean
    private GeneratedRouteRepository routeRepository;

    @Test
    void createsAndRunsJob() throws Exception {
        UUID projectId = UUID.randomUUID();
        UUID jobId = UUID.randomUUID();

        OptimizationJobResponse response = new OptimizationJobResponse(
                jobId,
                projectId,
                JobStatus.COMPLETED,
                "MULTI_OBJECTIVE_A_STAR",
                new BigDecimal("0.5000"),
                new BigDecimal("0.5000"),
                new BigDecimal("150.00"),
                new BigDecimal("33.00"),
                null,
                "{}",
                Instant.now(),
                Instant.now(),
                Instant.now()
        );

        when(jobService.createAndRunJob(eq(projectId), any())).thenReturn(response);

        mockMvc.perform(post("/api/v1/projects/{projectId}/jobs", projectId)
                        .contentType(MediaType.APPLICATION_JSON)
                        .content("""
                                {
                                  "algorithmType": "MULTI_OBJECTIVE_A_STAR",
                                  "scenario": "Balanced"
                                }
                                """))
                .andExpect(status().isCreated())
                .andExpect(jsonPath("$.id").value(jobId.toString()))
                .andExpect(jsonPath("$.projectId").value(projectId.toString()))
                .andExpect(jsonPath("$.status").value("COMPLETED"))
                .andExpect(jsonPath("$.algorithmType").value("MULTI_OBJECTIVE_A_STAR"));
    }

    @Test
    void getsJob() throws Exception {
        UUID projectId = UUID.randomUUID();
        UUID jobId = UUID.randomUUID();

        OptimizationJobResponse response = new OptimizationJobResponse(
                jobId,
                projectId,
                JobStatus.RUNNING,
                "MULTI_OBJECTIVE_A_STAR",
                new BigDecimal("0.5000"),
                new BigDecimal("0.5000"),
                new BigDecimal("150.00"),
                new BigDecimal("33.00"),
                null,
                null,
                Instant.now(),
                Instant.now(),
                null
        );

        when(jobService.getJob(projectId, jobId)).thenReturn(response);

        mockMvc.perform(get("/api/v1/projects/{projectId}/jobs/{jobId}", projectId, jobId))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.id").value(jobId.toString()))
                .andExpect(jsonPath("$.status").value("RUNNING"));
    }

    @Test
    void listsJobs() throws Exception {
        UUID projectId = UUID.randomUUID();
        UUID jobId = UUID.randomUUID();

        OptimizationJobResponse response = new OptimizationJobResponse(
                jobId,
                projectId,
                JobStatus.COMPLETED,
                "MULTI_OBJECTIVE_A_STAR",
                new BigDecimal("0.5000"),
                new BigDecimal("0.5000"),
                new BigDecimal("150.00"),
                new BigDecimal("33.00"),
                null,
                "{}",
                Instant.now(),
                Instant.now(),
                Instant.now()
        );

        when(jobService.listJobs(projectId)).thenReturn(List.of(response));

        mockMvc.perform(get("/api/v1/projects/{projectId}/jobs", projectId))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$[0].id").value(jobId.toString()))
                .andExpect(jsonPath("$[0].status").value("COMPLETED"));
    }
}
