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
 * What one conductor costs to erect, per kilometre of one circuit.
 *
 * <p>The engine computes {@code length_km × parallel_count × rate}, so a twin or quad bundle carries
 * the same rate as its single-circuit parent — entering a doubled rate for a twin conductor would
 * double the cost twice.
 *
 * <p>Coverage has to be complete across the cable catalogue. The run chooses the conductor, and one
 * the catalogue does not price yields {@code CABLE_COST_NOT_FOUND} and no total at all.
 */
@Entity
@Table(name = "conductor_cost_items")
public class ConductorCostItem {

    @Id
    @GeneratedValue
    private UUID id;

    @ManyToOne
    @JoinColumn(name = "catalogue_id", nullable = false)
    private CostCatalogue catalogue;

    @Column(name = "cable_type_id", nullable = false, length = 60)
    private String cableTypeId;

    @Column(name = "installed_cost_per_km_per_circuit", nullable = false, precision = 14, scale = 2)
    private BigDecimal installedCostPerKmPerCircuit;

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

    public String getCableTypeId() {
        return cableTypeId;
    }

    public BigDecimal getInstalledCostPerKmPerCircuit() {
        return installedCostPerKmPerCircuit;
    }

    public CableDataProvenance getDataProvenance() {
        return dataProvenance;
    }

    public String getSourceNote() {
        return sourceNote;
    }
}
