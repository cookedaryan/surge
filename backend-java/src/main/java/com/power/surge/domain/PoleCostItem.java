package com.power.surge.domain;

import jakarta.persistence.Column;
import jakarta.persistence.Entity;
import jakarta.persistence.EnumType;
import jakarta.persistence.Enumerated;
import jakarta.persistence.GeneratedValue;
import jakarta.persistence.Id;
import jakarta.persistence.JoinColumn;
import jakarta.persistence.ManyToOne;
import jakarta.persistence.Table;

import java.math.BigDecimal;
import java.util.UUID;

/**
 * What one pole of a given class costs to erect.
 *
 * <p>{@code poleType} is stored lowercase because that is the vocabulary Python validates against
 * ({@code terminal} / {@code angle} / {@code intermediate} / {@code junction}), and it matches the
 * classes the pole placement engine emits.
 */
@Entity
@Table(name = "pole_cost_items")
public class PoleCostItem {

    @Id
    @GeneratedValue
    private UUID id;

    @ManyToOne
    @JoinColumn(name = "catalogue_id", nullable = false)
    private CostCatalogue catalogue;

    @Column(name = "pole_type", nullable = false, length = 20)
    private String poleType;

    @Column(name = "installed_cost_each", nullable = false, precision = 14, scale = 2)
    private BigDecimal installedCostEach;

    @Enumerated(EnumType.STRING)
    @Column(name = "data_provenance", nullable = false, length = 20)
    private CableDataProvenance dataProvenance = CableDataProvenance.UNKNOWN;

    @Column(name = "source_note", length = 300)
    private String sourceNote;

    public UUID getId() {
        return id;
    }

    public CostCatalogue getCatalogue() {
        return catalogue;
    }

    public String getPoleType() {
        return poleType;
    }

    public BigDecimal getInstalledCostEach() {
        return installedCostEach;
    }

    public CableDataProvenance getDataProvenance() {
        return dataProvenance;
    }

    public String getSourceNote() {
        return sourceNote;
    }
}
