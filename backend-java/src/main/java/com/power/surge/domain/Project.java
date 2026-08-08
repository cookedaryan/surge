package com.power.surge.domain;

import jakarta.persistence.Column;
import jakarta.persistence.Entity;
import jakarta.persistence.Table;
import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.Size;
import org.locationtech.jts.geom.Polygon;

import java.util.Objects;

@Entity
@Table(name = "projects")
public class Project extends AuditableEntity {

    public static final String WGS84_CRS = "EPSG:4326";
    public static final int WGS84_SRID = 4326;

    @NotBlank
    @Size(max = 200)
    @Column(nullable = false, length = 200)
    private String name;

    @Column(columnDefinition = "TEXT")
    private String description;

    @Column(nullable = false, length = 32)
    private String crs = WGS84_CRS;

    @Column(columnDefinition = "geometry(Polygon, 4326)")
    private Polygon boundary;

    protected Project() {
    }

    public Project(String name, String description) {
        this.name = requireName(name);
        this.description = description;
    }

    public void updateDetails(String name, String description) {
        this.name = requireName(name);
        this.description = description;
    }

    public void setBoundary(Polygon boundary) {
        if (boundary != null && boundary.getSRID() != WGS84_SRID) {
            throw new IllegalArgumentException("Project boundary must use SRID 4326.");
        }
        this.boundary = boundary;
    }

    public String getName() {
        return name;
    }

    public String getDescription() {
        return description;
    }

    public String getCrs() {
        return crs;
    }

    public Polygon getBoundary() {
        return boundary;
    }

    private static String requireName(String name) {
        String value = Objects.requireNonNull(name, "Project name is required.").trim();
        if (value.isEmpty()) {
            throw new IllegalArgumentException("Project name must not be blank.");
        }
        if (value.length() > 200) {
            throw new IllegalArgumentException("Project name must not exceed 200 characters.");
        }
        return value;
    }
}
