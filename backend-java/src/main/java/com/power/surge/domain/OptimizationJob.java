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

    @Size(max = 60)
    @Column(name = "scenario", length = 60)
    private String scenario;

    @Column(name = "capex_weight", nullable = false, precision = 5, scale = 4)
    private BigDecimal capexWeight;

    @Column(name = "losses_weight", nullable = false, precision = 5, scale = 4)
    private BigDecimal lossesWeight;

    @Column(name = "max_span_meters", nullable = false, precision = 8, scale = 2)
    private BigDecimal maxSpanMeters;

    @Column(name = "voltage_kv", nullable = false, precision = 6, scale = 2)
    private BigDecimal voltageKv;

    /**
     * Run parameters that used to live only on the inbound request. A queued job is executed after
     * that request has gone, so anything it needs has to be on the row or it silently reverts to a
     * default.
     */
    @Column(name = "feeder_capacity_mw", nullable = false, precision = 8, scale = 3)
    private BigDecimal feederCapacityMw;

    @Column(name = "max_voltage_drop_pct", nullable = false, precision = 5, scale = 2)
    private BigDecimal maxVoltageDropPct;

    @Column(name = "row_width_m", nullable = false, precision = 6, scale = 2)
    private BigDecimal rowWidthM;

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
        this(project, algorithmType, null, capexWeight, lossesWeight, maxSpanMeters, voltageKv);
    }

    public OptimizationJob(
            Project project,
            String algorithmType,
            String scenario,
            BigDecimal capexWeight,
            BigDecimal lossesWeight,
            BigDecimal maxSpanMeters,
            BigDecimal voltageKv
    ) {
        this(project, algorithmType, scenario, capexWeight, lossesWeight, maxSpanMeters, voltageKv,
                null, null, null);
    }

    public OptimizationJob(
            Project project,
            String algorithmType,
            String scenario,
            BigDecimal capexWeight,
            BigDecimal lossesWeight,
            BigDecimal maxSpanMeters,
            BigDecimal voltageKv,
            BigDecimal feederCapacityMw,
            BigDecimal maxVoltageDropPct,
            BigDecimal rowWidthM
    ) {
        this.project = Objects.requireNonNull(project, "Project is required.");
        this.status = JobStatus.PENDING;
        this.algorithmType = algorithmType != null ? algorithmType.trim() : "MULTI_OBJECTIVE_A_STAR";
        this.scenario = scenario != null ? scenario.trim() : "Balanced";
        this.capexWeight = capexWeight != null ? capexWeight : new BigDecimal("0.5000");
        this.lossesWeight = lossesWeight != null ? lossesWeight : new BigDecimal("0.5000");
        this.maxSpanMeters = maxSpanMeters != null ? maxSpanMeters : new BigDecimal("150.00");
        this.voltageKv = voltageKv != null ? voltageKv : new BigDecimal("33.00");
        // Defaults mirror the API defaults, so a job always states the parameters it ran with.
        this.feederCapacityMw = feederCapacityMw != null ? feederCapacityMw : new BigDecimal("20.000");
        this.maxVoltageDropPct = maxVoltageDropPct != null ? maxVoltageDropPct : new BigDecimal("5.00");
        this.rowWidthM = rowWidthM != null ? rowWidthM : new BigDecimal("18.00");
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

    public String getScenario() {
        return scenario;
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

    public BigDecimal getFeederCapacityMw() {
        return feederCapacityMw;
    }

    public BigDecimal getMaxVoltageDropPct() {
        return maxVoltageDropPct;
    }

    public BigDecimal getRowWidthM() {
        return rowWidthM;
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

    /**
     * What the run cost, as the engine computed it.
     *
     * <p>All nullable, and deliberately so: a run with no cost catalogue, or one whose catalogue did
     * not price a conductor the run selected, genuinely has no cost. Null lets a report say "not
     * costed"; a zero would read as free.
     */
    @Column(name = "cost_currency", length = 3)
    private String costCurrency;

    @Column(name = "conductor_capex", precision = 16, scale = 2)
    private BigDecimal conductorCapex;

    @Column(name = "pole_capex", precision = 16, scale = 2)
    private BigDecimal poleCapex;

    @Column(name = "land_capex", precision = 16, scale = 2)
    private BigDecimal landCapex;

    @Column(name = "total_capex", precision = 16, scale = 2)
    private BigDecimal totalCapex;

    @Column(name = "annual_loss_energy_mwh", precision = 16, scale = 4)
    private BigDecimal annualLossEnergyMwh;

    @Column(name = "annual_loss_cost", precision = 16, scale = 2)
    private BigDecimal annualLossCost;

    @Column(name = "present_value_opex", precision = 16, scale = 2)
    private BigDecimal presentValueOpex;

    @Column(name = "lifecycle_cost", precision = 16, scale = 2)
    private BigDecimal lifecycleCost;

    @Column(name = "cost_catalogue_id", length = 60)
    private String costCatalogueId;

    @Column(name = "cost_catalogue_version", length = 30)
    private String costCatalogueVersion;

    @Column(name = "cost_price_basis_date", length = 30)
    private String costPriceBasisDate;

    /**
     * Components the engine could not price.
     *
     * <p>Above zero, the totals are incomplete by construction: the engine leaves a component null
     * rather than costing a gap at zero, so this count is what separates a total from a partial sum.
     */
    @Column(name = "cost_failure_count")
    private Integer costFailureCount;

    /** Records the money the engine computed for the network that was chosen. */
    public void applyCost(
            String currency,
            BigDecimal conductorCapex,
            BigDecimal poleCapex,
            BigDecimal landCapex,
            BigDecimal totalCapex,
            BigDecimal annualLossEnergyMwh,
            BigDecimal annualLossCost,
            BigDecimal presentValueOpex,
            BigDecimal lifecycleCost,
            String catalogueId,
            String catalogueVersion,
            String priceBasisDate,
            Integer failureCount
    ) {
        this.costCurrency = currency;
        this.conductorCapex = conductorCapex;
        this.poleCapex = poleCapex;
        this.landCapex = landCapex;
        this.totalCapex = totalCapex;
        this.annualLossEnergyMwh = annualLossEnergyMwh;
        this.annualLossCost = annualLossCost;
        this.presentValueOpex = presentValueOpex;
        this.lifecycleCost = lifecycleCost;
        this.costCatalogueId = catalogueId;
        this.costCatalogueVersion = catalogueVersion;
        this.costPriceBasisDate = priceBasisDate;
        this.costFailureCount = failureCount;
    }

    public String getCostCurrency() {
        return costCurrency;
    }

    public BigDecimal getConductorCapex() {
        return conductorCapex;
    }

    public BigDecimal getPoleCapex() {
        return poleCapex;
    }

    public BigDecimal getLandCapex() {
        return landCapex;
    }

    public BigDecimal getTotalCapex() {
        return totalCapex;
    }

    public BigDecimal getAnnualLossEnergyMwh() {
        return annualLossEnergyMwh;
    }

    public BigDecimal getAnnualLossCost() {
        return annualLossCost;
    }

    public BigDecimal getPresentValueOpex() {
        return presentValueOpex;
    }

    public BigDecimal getLifecycleCost() {
        return lifecycleCost;
    }

    public String getCostCatalogueId() {
        return costCatalogueId;
    }

    public String getCostCatalogueVersion() {
        return costCatalogueVersion;
    }

    public String getCostPriceBasisDate() {
        return costPriceBasisDate;
    }

    public Integer getCostFailureCount() {
        return costFailureCount;
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
