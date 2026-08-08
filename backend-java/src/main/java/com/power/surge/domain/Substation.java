package com.power.surge.domain;

import jakarta.persistence.Column;
import jakarta.persistence.Entity;
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
@Table(name = "substations")
public class Substation extends AuditableEntity {

    @ManyToOne(fetch = FetchType.LAZY, optional = false)
    @JoinColumn(name = "project_id", nullable = false, updatable = false)
    private Project project;

    @NotBlank
    @Size(max = 100)
    @Column(name = "external_id", nullable = false, length = 100)
    private String externalId;

    @Positive
    @Column(name = "capacity_mw", precision = 12, scale = 3)
    private BigDecimal capacityMw;

    @Column(nullable = false, columnDefinition = "geometry(Point, 4326)")
    private Point location;

    protected Substation() {
    }

    public Substation(Project project, String externalId, BigDecimal capacityMw, Point location) {
        this.project = Objects.requireNonNull(project, "Project is required.");
        this.externalId = requireExternalId(externalId);
        this.capacityMw = requirePositiveCapacity(capacityMw);
        this.location = requireWgs84Location(location);
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
        String value = Objects.requireNonNull(externalId, "Substation external ID is required.").trim();
        if (value.isEmpty()) {
            throw new IllegalArgumentException("Substation external ID must not be blank.");
        }
        if (value.length() > 100) {
            throw new IllegalArgumentException("Substation external ID must not exceed 100 characters.");
        }
        return value;
    }

    private static BigDecimal requirePositiveCapacity(BigDecimal capacityMw) {
        if (capacityMw != null && capacityMw.signum() <= 0) {
            throw new IllegalArgumentException("Substation capacity must be greater than zero.");
        }
        return capacityMw;
    }

    private static Point requireWgs84Location(Point location) {
        Point value = Objects.requireNonNull(location, "Substation location is required.");
        if (value.getSRID() != Project.WGS84_SRID) {
            throw new IllegalArgumentException("Substation location must use SRID 4326.");
        }
        return value;
    }
}
