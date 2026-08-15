package com.power.surge.service;

import com.power.surge.domain.JobStatus;
import com.power.surge.domain.OptimizationJob;
import com.power.surge.repository.OptimizationJobRepository;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.boot.context.event.ApplicationReadyEvent;
import org.springframework.context.event.EventListener;
import org.springframework.stereotype.Component;
import org.springframework.transaction.annotation.Transactional;

import java.util.List;

/**
 * Fails jobs that were mid-flight when the process died.
 *
 * <p>Optimisation state lives in the database while the work itself lives in an in-memory executor.
 * A graceful shutdown drains that executor, but a crash or a hard kill does not — and the row is
 * left saying RUNNING forever. Nothing would ever move it, so the UI would show an optimisation
 * that never finishes and never fails.
 *
 * <p>Runs once at startup, when no worker can legitimately be mid-run yet: this process has just
 * begun, so anything already marked as started belongs to an instance that is gone. Jobs are failed
 * rather than requeued, because the operator should decide whether to re-run rather than have work
 * silently restart underneath them.
 */
@Component
public class StaleJobSweeper {

    private static final Logger log = LoggerFactory.getLogger(StaleJobSweeper.class);

    private static final String MESSAGE =
            "The server restarted while this optimisation was running. Please run it again.";

    private final OptimizationJobRepository jobRepository;

    public StaleJobSweeper(OptimizationJobRepository jobRepository) {
        this.jobRepository = jobRepository;
    }

    @EventListener(ApplicationReadyEvent.class)
    @Transactional
    public void failJobsOrphanedByRestart() {
        List<OptimizationJob> orphaned = jobRepository.findAllByStatus(JobStatus.RUNNING);
        orphaned.addAll(jobRepository.findAllByStatus(JobStatus.PENDING));
        if (orphaned.isEmpty()) {
            return;
        }
        orphaned.forEach(job -> job.markFailed(MESSAGE));
        jobRepository.saveAll(orphaned);
        log.warn("Failed {} optimisation job(s) left unfinished by a previous run", orphaned.size());
    }
}
