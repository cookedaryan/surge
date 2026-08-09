package com.power.surge.controller;

import com.power.surge.service.OptimizationJobService;
import com.power.surge.service.SseProgressService;
import org.springframework.http.MediaType;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;
import org.springframework.web.servlet.mvc.method.annotation.SseEmitter;

import java.util.UUID;

@RestController
@RequestMapping("/api/v1/projects/{projectId}/jobs/{jobId}/progress")
public class JobProgressController {

    private final OptimizationJobService jobService;
    private final SseProgressService sseProgressService;

    public JobProgressController(OptimizationJobService jobService, SseProgressService sseProgressService) {
        this.jobService = jobService;
        this.sseProgressService = sseProgressService;
    }

    @GetMapping(produces = MediaType.TEXT_EVENT_STREAM_VALUE)
    public SseEmitter streamJobProgress(
            @PathVariable UUID projectId,
            @PathVariable UUID jobId
    ) {
        // Validate job existence and project ownership
        jobService.getJob(projectId, jobId);

        return sseProgressService.registerEmitter(jobId);
    }
}
