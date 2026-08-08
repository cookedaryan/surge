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
    public static OptimizationJobResponse fromEntity(OptimizationJob job) {
        return new OptimizationJobResponse(
                job.getId(),
                job.getProject().getId(),
                job.getStatus(),
                job.getAlgorithmType(),
                job.getCapexWeight(),
                job.getLossesWeight(),
                job.getMaxSpanMeters(),
                job.getVoltageKv(),
                job.getErrorMessage(),
                job.getResultSummaryJson(),
                job.getCreatedAt(),
                job.getStartedAt(),
                job.getCompletedAt()
        );
    }
}
