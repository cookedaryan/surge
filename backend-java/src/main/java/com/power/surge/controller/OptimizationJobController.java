package com.power.surge.controller;

import com.power.surge.dto.job.CreateOptimizationJobRequest;
import com.power.surge.dto.job.OptimizationJobResponse;
import com.power.surge.service.OptimizationJobService;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

import java.util.List;
import java.util.UUID;

@RestController
@RequestMapping("/api/v1/projects/{projectId}/jobs")
public class OptimizationJobController {

    private final OptimizationJobService jobService;

    public OptimizationJobController(OptimizationJobService jobService) {
        this.jobService = jobService;
    }

    @PostMapping
    public ResponseEntity<OptimizationJobResponse> createAndRunJob(
            @PathVariable UUID projectId,
            @RequestBody(required = false) CreateOptimizationJobRequest request
    ) {
        OptimizationJobResponse response = jobService.createAndRunJob(projectId, request);
        return ResponseEntity.status(HttpStatus.CREATED).body(response);
    }

    @GetMapping("/{jobId}")
    public OptimizationJobResponse getJob(
            @PathVariable UUID projectId,
            @PathVariable UUID jobId
    ) {
        return jobService.getJob(projectId, jobId);
    }

    @GetMapping
    public List<OptimizationJobResponse> listJobs(@PathVariable UUID projectId) {
        return jobService.listJobs(projectId);
    }
}
