package com.power.surge.dto.job;

import com.power.surge.domain.JobStatus;
import com.power.surge.domain.OptimizationJob;

import java.math.BigDecimal;
import java.time.Instant;
import java.util.UUID;

public record OptimizationJobResponse(
        UUID id,
        UUID projectId,
        JobStatus status,
        String algorithmType,
        String scenario,
        BigDecimal capexWeight,
        BigDecimal lossesWeight,
        BigDecimal maxSpanMeters,
        BigDecimal voltageKv,
        String errorMessage,
        String resultSummaryJson,
        Instant createdAt,
        Instant startedAt,
        Instant completedAt,
        /** The policy behind the recommendation (C2), or null when the job has none recorded. */
        EffectiveProfileResponse effectiveProfile
) {

    /** A job with no recorded policy: the shape this response had before profiles existed. */
    public OptimizationJobResponse(
            UUID id,
            UUID projectId,
            JobStatus status,
            String algorithmType,
            String scenario,
            BigDecimal capexWeight,
            BigDecimal lossesWeight,
            BigDecimal maxSpanMeters,
            BigDecimal voltageKv,
            String errorMessage,
            String resultSummaryJson,
            Instant createdAt,
            Instant startedAt,
            Instant completedAt
    ) {
        this(id, projectId, status, algorithmType, scenario, capexWeight, lossesWeight,
                maxSpanMeters, voltageKv, errorMessage, resultSummaryJson, createdAt, startedAt,
                completedAt, null);
    }

    public static OptimizationJobResponse fromEntity(OptimizationJob job) {
        return new OptimizationJobResponse(
                job.getId(),
                job.getProject().getId(),
                job.getStatus(),
                job.getAlgorithmType(),
                job.getScenario(),
                job.getCapexWeight(),
                job.getLossesWeight(),
                job.getMaxSpanMeters(),
                job.getVoltageKv(),
                job.getErrorMessage(),
                job.getResultSummaryJson(),
                job.getCreatedAt(),
                job.getStartedAt(),
                job.getCompletedAt(),
                EffectiveProfileResponse.fromEntity(job)
        );
    }
}
