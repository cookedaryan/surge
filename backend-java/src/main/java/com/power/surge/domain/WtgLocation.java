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
import jakarta.validation.constraints.Positive;
import jakarta.validation.constraints.Size;
import org.locationtech.jts.geom.Point;

import java.math.BigDecimal;
import java.util.Objects;

@Entity
@Table(name = "wtg_locations")
public class WtgLocation extends AuditableEntity {

    @ManyToOne(fetch = FetchType.LAZY, optional = false)
    @JoinColumn(name = "project_id", nullable = false, updatable = false)
    private Project project;

    @NotBlank
    @Size(max = 100)
    @Column(name = "external_id", nullable = false, length = 100)
    private String externalId;

    @Positive
    @Column(name = "capacity_mw", nullable = false, precision = 12, scale = 3)
    private BigDecimal capacityMw;

    @Column(nullable = false, columnDefinition = "geometry(Point, 4326)")
    private Point location;

    /**
     * Micro-siting lifecycle status. Only statuses where {@link WtgStatus#isOptimisable()} is true
     * are sent to the optimisation engine, so cancelled and low-AEP locations no longer distort
     * feeder grouping.
     */
    @Enumerated(EnumType.STRING)
    @Column(name = "status", nullable = false, length = 32)
    private WtgStatus status = WtgStatus.UNKNOWN;

    /** KML folder path this asset was imported from. Retained for audit and re-classification. */
    @Size(max = 255)
    @Column(name = "source_folder", length = 255)
    private String sourceFolder;

    protected WtgLocation() {
    }

    /**
     * Creates a turbine entered directly through the API. Such turbines are {@link WtgStatus#APPROVED}
     * by definition — an operator adding a location by hand intends it to be part of the network.
     */
    public WtgLocation(Project project, String externalId, BigDecimal capacityMw, Point location) {
        this(project, externalId, capacityMw, location, WtgStatus.APPROVED, null);
    }

    public WtgLocation(
            Project project,
            String externalId,
            BigDecimal capacityMw,
            Point location,
            WtgStatus status,
            String sourceFolder
    ) {
        this.project = Objects.requireNonNull(project, "Project is required.");
        this.externalId = requireExternalId(externalId);
        this.capacityMw = requirePositiveCapacity(capacityMw);
        this.location = requireWgs84Location(location);
        this.status = status == null ? WtgStatus.UNKNOWN : status;
        this.sourceFolder = trimToNull(sourceFolder);
    }

    public WtgStatus getStatus() {
        return status;
    }

    public String getSourceFolder() {
        return sourceFolder;
    }

    private static String trimToNull(String value) {
        if (value == null) {
            return null;
        }
        String trimmed = value.trim();
        if (trimmed.isEmpty()) {
            return null;
        }
        return trimmed.length() > 255 ? trimmed.substring(0, 255) : trimmed;
    }

    public Project getProject() {
        return project;
    }

    public String getExternalId() {
        return externalId;
    }

    public BigDecimal getCapacityMw() {
        return capacityMw;
    }

    public Point getLocation() {
        return location;
    }

    private static String requireExternalId(String externalId) {
        String value = Objects.requireNonNull(externalId, "WTG external ID is required.").trim();
        if (value.isEmpty()) {
            throw new IllegalArgumentException("WTG external ID must not be blank.");
        }
        if (value.length() > 100) {
            throw new IllegalArgumentException("WTG external ID must not exceed 100 characters.");
        }
        return value;
    }

    private static BigDecimal requirePositiveCapacity(BigDecimal capacityMw) {
        BigDecimal value = Objects.requireNonNull(capacityMw, "WTG capacity is required.");
        if (value.signum() <= 0) {
            throw new IllegalArgumentException("WTG capacity must be greater than zero.");
        }
        return value;
    }

    private static Point requireWgs84Location(Point location) {
        Point value = Objects.requireNonNull(location, "WTG location is required.");
        if (value.getSRID() != Project.WGS84_SRID) {
            throw new IllegalArgumentException("WTG location must use SRID 4326.");
        }
        return value;
    }
}
