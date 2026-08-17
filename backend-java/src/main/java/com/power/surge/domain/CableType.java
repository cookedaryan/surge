package com.power.surge.domain;

import jakarta.persistence.Column;
import jakarta.persistence.Entity;
import jakarta.persistence.EnumType;
import jakarta.persistence.Enumerated;
import jakarta.persistence.GeneratedValue;
import jakarta.persistence.Id;
import jakarta.persistence.Table;

import java.math.BigDecimal;
import java.time.Instant;
import java.util.UUID;

/**
 * One conductor the optimiser may choose between when sizing a segment.
 *
 * <p>Before this existed the engine had a single fictional cable to work with, so per-segment
 * sizing had nothing to select and every electrical figure rested on placeholder impedances.
 */
@Entity
@Table(name = "cable_types")
public class CableType {

    @Id
    @GeneratedValue
    private UUID id;

    @Column(name = "cable_type_id", nullable = false, unique = true, length = 60)
    private String cableTypeId;

    @Column(name = "display_name", nullable = false, length = 120)
    private String displayName;

    @Column(name = "nominal_voltage_kv", nullable = false, precision = 6, scale = 2)
    private BigDecimal nominalVoltageKv;

    @Column(name = "resistance_ohm_per_km", nullable = false, precision = 10, scale = 5)
    private BigDecimal resistanceOhmPerKm;

    @Column(name = "reactance_ohm_per_km", nullable = false, precision = 10, scale = 5)
    private BigDecimal reactanceOhmPerKm;

    @Column(name = "capacitance_nf_per_km", nullable = false, precision = 10, scale = 3)
    private BigDecimal capacitanceNfPerKm;

    @Column(name = "max_current_a", nullable = false, precision = 10, scale = 2)
    private BigDecimal maxCurrentA;

    @Column(name = "parallel_count", nullable = false)
    private Integer parallelCount = 1;

    @Column(name = "derating_factor", nullable = false, precision = 4, scale = 3)
    private BigDecimal deratingFactor = BigDecimal.ONE;

    /**
     * Whether anyone has checked these figures against a datasheet.
     *
     * <p>Unverified parameters produce results that look exactly as authoritative as verified ones,
     * so the distinction has to travel with the data rather than live in someone's memory.
     */
    @Enumerated(EnumType.STRING)
    @Column(name = "data_provenance", nullable = false, length = 20)
    private CableDataProvenance dataProvenance = CableDataProvenance.UNKNOWN;

    @Column(name = "source_note", length = 300)
    private String sourceNote;

    @Column(name = "enabled", nullable = false)
    private boolean enabled = true;

    @Column(name = "created_at", nullable = false)
    private Instant createdAt = Instant.now();

    protected CableType() {
    }

    public UUID getId() {
        return id;
    }

    public String getCableTypeId() {
        return cableTypeId;
    }

    public String getDisplayName() {
        return displayName;
    }

    public BigDecimal getNominalVoltageKv() {
        return nominalVoltageKv;
    }

    public BigDecimal getResistanceOhmPerKm() {
        return resistanceOhmPerKm;
    }

    public BigDecimal getReactanceOhmPerKm() {
        return reactanceOhmPerKm;
    }

    public BigDecimal getCapacitanceNfPerKm() {
        return capacitanceNfPerKm;
    }

    public BigDecimal getMaxCurrentA() {
        return maxCurrentA;
    }

    public Integer getParallelCount() {
        return parallelCount;
    }

    public BigDecimal getDeratingFactor() {
        return deratingFactor;
    }

    public CableDataProvenance getDataProvenance() {
        return dataProvenance;
    }

    public String getSourceNote() {
        return sourceNote;
    }

    public boolean isEnabled() {
        return enabled;
    }

    public Instant getCreatedAt() {
        return createdAt;
    }
}
