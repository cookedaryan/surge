package com.power.surge.controller;

import com.power.surge.domain.JobStatus;
import com.power.surge.dto.job.OptimizationJobResponse;
import com.power.surge.service.OptimizationJobService;
import com.power.surge.service.SseProgressService;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.autoconfigure.web.servlet.WebMvcTest;
import org.springframework.boot.test.mock.mockito.MockBean;
import org.springframework.http.MediaType;
import org.springframework.test.web.servlet.MockMvc;
import org.springframework.web.servlet.mvc.method.annotation.SseEmitter;

import java.math.BigDecimal;
import java.time.Instant;
import java.util.UUID;

import static org.mockito.ArgumentMatchers.eq;
import static org.mockito.Mockito.when;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.content;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

import org.springframework.boot.test.autoconfigure.web.servlet.AutoConfigureMockMvc;
import com.power.surge.security.JwtTokenProvider;

@WebMvcTest(JobProgressController.class)
@AutoConfigureMockMvc(addFilters = false)
class JobProgressControllerTest {

    @Autowired
    private MockMvc mockMvc;

    @MockBean
    private JwtTokenProvider jwtTokenProvider;

    @MockBean
    private com.power.surge.service.AuthService authService;

    @MockBean
    private OptimizationJobService jobService;

    @MockBean
    private SseProgressService sseProgressService;

    @Test
    void streamJobProgress_returnsSseStream() throws Exception {
        UUID projectId = UUID.randomUUID();
        UUID jobId = UUID.randomUUID();

        OptimizationJobResponse dummyJob = new OptimizationJobResponse(
                jobId, projectId, JobStatus.RUNNING, "MULTI_OBJECTIVE_A_STAR", "Balanced",
                new BigDecimal("0.5000"), new BigDecimal("0.5000"), new BigDecimal("150.00"),
                new BigDecimal("33.00"), null, "{}", Instant.now(), Instant.now(), null
        );

        when(jobService.getJob(eq(projectId), eq(jobId))).thenReturn(dummyJob);
        when(sseProgressService.registerEmitter(eq(jobId))).thenReturn(new SseEmitter());

        mockMvc.perform(get("/api/v1/projects/{projectId}/jobs/{jobId}/progress", projectId, jobId))
                .andExpect(status().isOk())
                .andExpect(org.springframework.test.web.servlet.result.MockMvcResultMatchers.request().asyncStarted());
    }
}
