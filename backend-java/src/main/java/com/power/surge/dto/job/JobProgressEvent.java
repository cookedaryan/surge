package com.power.surge.dto.job;

import com.power.surge.domain.JobStatus;

import java.time.Instant;
import java.util.UUID;

public record JobProgressEvent(
        UUID jobId,
        JobStatus status,
        int progressPercent,
        String message,
        Instant timestamp
) {
    public static JobProgressEvent of(UUID jobId, JobStatus status, int progressPercent, String message) {
        return new JobProgressEvent(jobId, status, progressPercent, message, Instant.now());
    }
}
