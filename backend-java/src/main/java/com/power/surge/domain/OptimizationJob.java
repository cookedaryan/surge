package com.power.surge.domain;

import jakarta.persistence.Column;
import jakarta.persistence.Entity;
import jakarta.persistence.EnumType;
import jakarta.persistence.Enumerated;
import jakarta.persistence.FetchType;
import jakarta.persistence.JoinColumn;
import jakarta.persistence.ManyToOne;
import jakarta.persistence.Table;
import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.NotNull;
import jakarta.validation.constraints.Size;

import java.math.BigDecimal;
import java.time.Instant;
import java.util.Objects;

@Entity
@Table(name = "optimization_jobs")
public class OptimizationJob extends AuditableEntity {

    @ManyToOne(fetch = FetchType.LAZY, optional = false)
    @JoinColumn(name = "project_id", nullable = false, updatable = false)
    private Project project;

    @NotNull
    @Enumerated(EnumType.STRING)
    @Column(name = "status", nullable = false, length = 32)
    private JobStatus status;

    @NotBlank
    @Size(max = 50)
    @Column(name = "algorithm_type", nullable = false, length = 50)
    private String algorithmType;

    @Column(name = "capex_weight", nullable = false, precision = 5, scale = 4)
    private BigDecimal capexWeight;

    @Column(name = "losses_weight", nullable = false, precision = 5, scale = 4)
    private BigDecimal lossesWeight;

    @Column(name = "max_span_meters", nullable = false, precision = 8, scale = 2)
    private BigDecimal maxSpanMeters;

    @Column(name = "voltage_kv", nullable = false, precision = 6, scale = 2)
    private BigDecimal voltageKv;

    @Column(name = "error_message", columnDefinition = "TEXT")
    private String errorMessage;

    @Column(name = "result_summary_json", columnDefinition = "TEXT")
    private String resultSummaryJson;

    @Column(name = "started_at")
    private Instant startedAt;

    @Column(name = "completed_at")
    private Instant completedAt;

    protected OptimizationJob() {
    }

    public OptimizationJob(
            Project project,
            String algorithmType,
            BigDecimal capexWeight,
            BigDecimal lossesWeight,
            BigDecimal maxSpanMeters,
            BigDecimal voltageKv
    ) {
        this.project = Objects.requireNonNull(project, "Project is required.");
        this.status = JobStatus.PENDING;
        this.algorithmType = algorithmType != null ? algorithmType.trim() : "MULTI_OBJECTIVE_A_STAR";
        this.capexWeight = capexWeight != null ? capexWeight : new BigDecimal("0.5000");
        this.lossesWeight = lossesWeight != null ? lossesWeight : new BigDecimal("0.5000");
        this.maxSpanMeters = maxSpanMeters != null ? maxSpanMeters : new BigDecimal("150.00");
        this.voltageKv = voltageKv != null ? voltageKv : new BigDecimal("33.00");
    }

    public Project getProject() {
        return project;
    }

    public JobStatus getStatus() {
        return status;
    }

    public String getAlgorithmType() {
        return algorithmType;
    }

    public BigDecimal getCapexWeight() {
        return capexWeight;
    }

    public BigDecimal getLossesWeight() {
        return lossesWeight;
    }

    public BigDecimal getMaxSpanMeters() {
        return maxSpanMeters;
    }

    public BigDecimal getVoltageKv() {
        return voltageKv;
    }

    public String getErrorMessage() {
        return errorMessage;
    }

    public String getResultSummaryJson() {
        return resultSummaryJson;
    }

    public Instant getStartedAt() {
        return startedAt;
    }

    public Instant getCompletedAt() {
        return completedAt;
    }

    public void markRunning() {
        this.status = JobStatus.RUNNING;
        this.startedAt = Instant.now();
    }

    public void markCompleted(String summaryJson) {
        this.status = JobStatus.COMPLETED;
        this.resultSummaryJson = summaryJson;
        this.completedAt = Instant.now();
    }

    public void markFailed(String errorMessage) {
        markFailed(errorMessage, null);
    }

    /** Also records the diagnostic summary (rejected candidates, reasons) behind the failure. */
    public void markFailed(String errorMessage, String summaryJson) {
        this.status = JobStatus.FAILED;
        this.errorMessage = errorMessage;
        this.resultSummaryJson = summaryJson;
        this.completedAt = Instant.now();
    }

    public void markCancelled() {
        this.status = JobStatus.CANCELLED;
        this.completedAt = Instant.now();
    }
}
