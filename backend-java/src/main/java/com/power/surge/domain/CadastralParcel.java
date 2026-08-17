package com.power.surge.domain;

import jakarta.persistence.Column;
import jakarta.persistence.Entity;
import jakarta.persistence.FetchType;
import jakarta.persistence.JoinColumn;
import jakarta.persistence.ManyToOne;
import jakarta.persistence.Table;
import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.Size;
import org.locationtech.jts.geom.Polygon;

import java.math.BigDecimal;
import java.util.Objects;

@Entity
@Table(name = "cadastral_parcels")
public class CadastralParcel extends AuditableEntity {

    @ManyToOne(fetch = FetchType.LAZY, optional = false)
    @JoinColumn(name = "project_id", nullable = false, updatable = false)
    private Project project;

    @NotBlank
    @Size(max = 100)
    @Column(name = "parcel_id", nullable = false, length = 100)
    private String parcelId;

    @Size(max = 200)
    @Column(name = "owner_name", length = 200)
    private String ownerName;

    @Column(name = "owner_id")
    private java.util.UUID ownerId;

    @Column(name = "availability_status", length = 50)
    private String availabilityStatus;

    @Column(name = "transaction_mode", length = 50)
    private String transactionMode;

    @Column(name = "price_status", length = 50)
    private String priceStatus;

    @Column(name = "price_date", length = 30)
    private String priceDate;

    @Column(name = "acquisition_cost_per_m2", precision = 14, scale = 2)
    private BigDecimal acquisitionCostPerM2;

    @Column(nullable = false, columnDefinition = "geometry(Polygon, 4326)")
    private Polygon geometry;

    protected CadastralParcel() {
    }

    public CadastralParcel(Project project, String parcelId, String ownerName, BigDecimal acquisitionCostPerM2, Polygon geometry) {
        this.project = Objects.requireNonNull(project, "Project is required.");
        this.parcelId = requireParcelId(parcelId);
        this.ownerName = ownerName;
        this.acquisitionCostPerM2 = requireNonNegativeCost(acquisitionCostPerM2);
        this.geometry = requireWgs84Polygon(geometry);
    }

    public Project getProject() {
        return project;
    }

    public String getParcelId() {
        return parcelId;
    }

    public String getOwnerName() {
        return ownerName;
    }

    public java.util.UUID getOwnerId() {
        return ownerId;
    }

    public String getAvailabilityStatus() {
        return availabilityStatus;
    }

    public String getTransactionMode() {
        return transactionMode;
    }

    public String getPriceStatus() {
        return priceStatus;
    }

    public String getPriceDate() {
        return priceDate;
    }

    public BigDecimal getAcquisitionCostPerM2() {
        return acquisitionCostPerM2;
    }

    public Polygon getGeometry() {
        return geometry;
    }

    public void updateCommercialDetails(java.util.UUID ownerId, String availabilityStatus, String transactionMode, String priceStatus, String priceDate, BigDecimal acquisitionCostPerM2) {
        this.ownerId = ownerId;
        this.availabilityStatus = availabilityStatus;
        this.transactionMode = transactionMode;
        this.priceStatus = priceStatus;
        this.priceDate = priceDate;
        this.acquisitionCostPerM2 = requireNonNegativeCost(acquisitionCostPerM2);
    }

    private static String requireParcelId(String parcelId) {
        String value = Objects.requireNonNull(parcelId, "Parcel ID is required.").trim();
        if (value.isEmpty()) {
            throw new IllegalArgumentException("Parcel ID must not be blank.");
        }
        if (value.length() > 100) {
            throw new IllegalArgumentException("Parcel ID must not exceed 100 characters.");
        }
        return value;
    }

    private static BigDecimal requireNonNegativeCost(BigDecimal cost) {
        if (cost != null && cost.signum() < 0) {
            throw new IllegalArgumentException("Acquisition cost per m2 must not be negative.");
        }
        return cost;
    }

    private static Polygon requireWgs84Polygon(Polygon polygon) {
        Polygon value = Objects.requireNonNull(polygon, "Parcel geometry is required.");
        if (value.getSRID() != Project.WGS84_SRID) {
            throw new IllegalArgumentException("Parcel geometry must use SRID 4326.");
        }
        return value;
    }
}
