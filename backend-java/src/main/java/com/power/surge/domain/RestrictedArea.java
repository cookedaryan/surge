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
@Table(name = "restricted_areas")
public class RestrictedArea extends AuditableEntity {

    @ManyToOne(fetch = FetchType.LAZY, optional = false)
    @JoinColumn(name = "project_id", nullable = false, updatable = false)
    private Project project;

    @NotBlank
    @Size(max = 150)
    @Column(name = "name", nullable = false, length = 150)
    private String name;

    @NotBlank
    @Size(max = 50)
    @Column(name = "restriction_type", nullable = false, length = 50)
    private String restrictionType;

    @Column(name = "buffer_meters", nullable = false, precision = 8, scale = 2)
    private BigDecimal bufferMeters;

    @Column(nullable = false, columnDefinition = "geometry(Polygon, 4326)")
    private Polygon geometry;

    protected RestrictedArea() {
    }

    public RestrictedArea(Project project, String name, String restrictionType, BigDecimal bufferMeters, Polygon geometry) {
        this.project = Objects.requireNonNull(project, "Project is required.");
        this.name = requireName(name);
        this.restrictionType = requireRestrictionType(restrictionType);
        this.bufferMeters = requireNonNegativeBuffer(bufferMeters);
        this.geometry = requireWgs84Polygon(geometry);
    }

    public Project getProject() {
        return project;
    }

    public String getName() {
        return name;
    }

    public String getRestrictionType() {
        return restrictionType;
    }

    public BigDecimal getBufferMeters() {
        return bufferMeters;
    }

    public Polygon getGeometry() {
        return geometry;
    }

    private static String requireName(String name) {
        String value = Objects.requireNonNull(name, "Restricted area name is required.").trim();
        if (value.isEmpty()) {
            throw new IllegalArgumentException("Restricted area name must not be blank.");
        }
        if (value.length() > 150) {
            throw new IllegalArgumentException("Restricted area name must not exceed 150 characters.");
        }
        return value;
    }

    private static String requireRestrictionType(String restrictionType) {
        String value = Objects.requireNonNull(restrictionType, "Restriction type is required.").trim();
        if (value.isEmpty()) {
            throw new IllegalArgumentException("Restriction type must not be blank.");
        }
        if (value.length() > 50) {
            throw new IllegalArgumentException("Restriction type must not exceed 50 characters.");
        }
        return value;
    }

    private static BigDecimal requireNonNegativeBuffer(BigDecimal bufferMeters) {
        BigDecimal value = bufferMeters != null ? bufferMeters : BigDecimal.ZERO;
        if (value.signum() < 0) {
            throw new IllegalArgumentException("Buffer meters must not be negative.");
        }
        return value;
    }

    private static Polygon requireWgs84Polygon(Polygon polygon) {
        Polygon value = Objects.requireNonNull(polygon, "Restricted area geometry is required.");
        if (value.getSRID() != Project.WGS84_SRID) {
            throw new IllegalArgumentException("Restricted area geometry must use SRID 4326.");
        }
        return value;
    }
}
