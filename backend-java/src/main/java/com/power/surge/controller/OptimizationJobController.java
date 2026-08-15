package com.power.surge.controller;

import com.power.surge.dto.job.CreateOptimizationJobRequest;
import com.power.surge.dto.job.OptimizationJobResponse;
import com.power.surge.service.OptimizationJobRunner;
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
import java.util.concurrent.RejectedExecutionException;

@RestController
@RequestMapping("/api/v1/projects/{projectId}/jobs")
public class OptimizationJobController {

    private final OptimizationJobService jobService;
    private final OptimizationJobRunner jobRunner;

    public OptimizationJobController(OptimizationJobService jobService, OptimizationJobRunner jobRunner) {
        this.jobService = jobService;
        this.jobRunner = jobRunner;
    }

    /**
     * Queues an optimisation run and returns immediately.
     *
     * <p>Returns 202 with the job in {@code PENDING}: a real solve takes tens of seconds, and
     * running it inside this request held a connection open for the duration. Clients follow the
     * job through its progress stream or by polling {@code GET /jobs/{jobId}}.
     *
     * <p>Validation still happens synchronously, so an unrunnable project is rejected here rather
     * than becoming a job that fails moments later.
     */
    @PostMapping
    public ResponseEntity<OptimizationJobResponse> createAndRunJob(
            @PathVariable UUID projectId,
            @RequestBody(required = false) CreateOptimizationJobRequest request
    ) {
        OptimizationJobResponse queued = jobService.createJob(projectId, request);
        try {
            // Submitted only after createJob's transaction has committed, so the worker can read it.
            jobRunner.submit(queued.id());
        } catch (RejectedExecutionException e) {
            jobService.markJobFailed(queued.id(),
                    "The optimisation queue is full. Please try again once running jobs finish.");
            return ResponseEntity.status(HttpStatus.SERVICE_UNAVAILABLE)
                    .body(jobService.getJob(projectId, queued.id()));
        }
        return ResponseEntity.accepted().body(queued);
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
