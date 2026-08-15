package com.power.surge.service;

import com.power.surge.config.AsyncConfig;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.scheduling.annotation.Async;
import org.springframework.stereotype.Component;

import java.util.UUID;

/**
 * Runs queued optimisation jobs off the request thread.
 *
 * <p>Deliberately a separate bean from {@link OptimizationJobService}: Spring's {@code @Async}
 * works through a proxy, so a service calling its own async method would simply run it inline and
 * the whole change would be silently undone.
 *
 * <p>The caller must have committed the job row before submitting. The worker reads the job back by
 * id in its own transaction and would not see an uncommitted one.
 */
@Component
public class OptimizationJobRunner {

    private static final Logger log = LoggerFactory.getLogger(OptimizationJobRunner.class);

    private final OptimizationJobService jobService;

    public OptimizationJobRunner(OptimizationJobService jobService) {
        this.jobService = jobService;
    }

    @Async(AsyncConfig.OPTIMIZATION_EXECUTOR)
    public void submit(UUID jobId) {
        try {
            log.info("Running optimisation job {}", jobId);
            // Committed separately so the job is observably RUNNING for the whole solve, rather
            // than appearing queued until the moment it finishes.
            jobService.markJobRunning(jobId);
            jobService.executeJob(jobId);
        } catch (Exception e) {
            // executeJob records its own failures. Anything reaching here failed outside that
            // handling, and must still leave the job in a terminal state rather than RUNNING
            // forever, which the UI would show as an optimisation that never finishes.
            log.error("Optimisation job {} failed outside its own error handling", jobId, e);
            jobService.markJobFailed(jobId, "Optimization failed unexpectedly: " + e.getMessage());
        }
    }
}
