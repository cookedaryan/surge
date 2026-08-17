package com.power.surge.domain;

import jakarta.persistence.CascadeType;
import jakarta.persistence.Column;
import jakarta.persistence.Entity;
import jakarta.persistence.EnumType;
import jakarta.persistence.Enumerated;
import jakarta.persistence.GeneratedValue;
import jakarta.persistence.Id;
import jakarta.persistence.OneToMany;
import jakarta.persistence.Table;

import java.math.BigDecimal;
import java.time.Instant;
import java.time.LocalDate;
import java.util.ArrayList;
import java.util.List;
import java.util.Set;
import java.util.UUID;

/**
 * The commercial rates a run is costed against.
 *
 * <p>Python computes CAPEX, land cost, loss valuation and a lifecycle total, but only for a request
 * carrying a {@code costing_config}. Java never sent one, so every candidate arrived with
 * {@code cost: null} while the product displayed money derived from {@code route length × 80} — a
 * constant with no basis and no currency.
 *
 * <p>The lifecycle parameters live here rather than in a table of their own because a catalogue
 * version pins the discount rate and energy price it was priced against. A lifecycle cost quoted
 * from one year's rates against another year's energy price is not comparable to anything.
 */
@Entity
@Table(name = "cost_catalogues")
public class CostCatalogue {

    @Id
    @GeneratedValue
    private UUID id;

    @Column(name = "catalogue_id", nullable = false, unique = true, length = 60)
    private String catalogueId;

    @Column(name = "version", nullable = false, length = 30)
    private String version;

    /** ISO 4217. Every rate in the catalogue is in this unit; nothing here converts currencies. */
    @Column(name = "currency", nullable = false, length = 3)
    private String currency;

    @Column(name = "price_basis_date", nullable = false)
    private LocalDate priceBasisDate;

    @Column(name = "land_fixed_cost_per_parcel", nullable = false, precision = 14, scale = 2)
    private BigDecimal landFixedCostPerParcel = BigDecimal.ZERO;

    @Column(name = "land_variable_basis", nullable = false, length = 30)
    private String landVariableBasis = "NONE";

    @Column(name = "land_variable_rate", nullable = false, precision = 14, scale = 4)
    private BigDecimal landVariableRate = BigDecimal.ZERO;

    @Column(name = "analysis_period_years", nullable = false)
    private Integer analysisPeriodYears;

    @Column(name = "discount_rate", nullable = false, precision = 6, scale = 4)
    private BigDecimal discountRate;

    @Column(name = "annual_operating_hours", nullable = false)
    private Integer annualOperatingHours;

    @Column(name = "loss_load_factor", nullable = false, precision = 5, scale = 4)
    private BigDecimal lossLoadFactor;

    @Column(name = "energy_price_per_mwh", nullable = false, precision = 14, scale = 2)
    private BigDecimal energyPricePerMwh;

    @Column(name = "energy_price_basis_date", nullable = false)
    private LocalDate energyPriceBasisDate;

    @Enumerated(EnumType.STRING)
    @Column(name = "data_provenance", nullable = false, length = 20)
    private CableDataProvenance dataProvenance = CableDataProvenance.UNKNOWN;

    @Column(name = "source_note", length = 300)
    private String sourceNote;

    @Column(name = "enabled", nullable = false)
    private boolean enabled = true;

    @Column(name = "created_at", nullable = false)
    private Instant createdAt = Instant.now();

    @Column(name = "updated_at", nullable = false)
    private Instant updatedAt = Instant.now();

    @OneToMany(mappedBy = "catalogue", cascade = CascadeType.ALL, orphanRemoval = true)
    private Set<ConductorCostItem> conductorItems = new java.util.LinkedHashSet<>();

    @OneToMany(mappedBy = "catalogue", cascade = CascadeType.ALL, orphanRemoval = true)
    private Set<PoleCostItem> poleItems = new java.util.LinkedHashSet<>();

    public UUID getId() {
        return id;
    }

    public String getCatalogueId() {
        return catalogueId;
    }

    public String getVersion() {
        return version;
    }

    public String getCurrency() {
        return currency;
    }

    public LocalDate getPriceBasisDate() {
        return priceBasisDate;
    }

    public BigDecimal getLandFixedCostPerParcel() {
        return landFixedCostPerParcel;
    }

    public String getLandVariableBasis() {
        return landVariableBasis;
    }

    public BigDecimal getLandVariableRate() {
        return landVariableRate;
    }

    public Integer getAnalysisPeriodYears() {
        return analysisPeriodYears;
    }

    public BigDecimal getDiscountRate() {
        return discountRate;
    }

    public Integer getAnnualOperatingHours() {
        return annualOperatingHours;
    }

    public BigDecimal getLossLoadFactor() {
        return lossLoadFactor;
    }

    public BigDecimal getEnergyPricePerMwh() {
        return energyPricePerMwh;
    }

    public LocalDate getEnergyPriceBasisDate() {
        return energyPriceBasisDate;
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

    public Set<ConductorCostItem> getConductorItems() {
        return conductorItems;
    }

    public Set<PoleCostItem> getPoleItems() {
        return poleItems;
    }
}
