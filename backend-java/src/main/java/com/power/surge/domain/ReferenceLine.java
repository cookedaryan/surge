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
import jakarta.validation.constraints.Size;
import org.locationtech.jts.geom.LineString;

import java.math.BigDecimal;
import java.util.Objects;

/**
 * An existing linear feature of the site: road, HT/EHV line, watercourse or prior route.
 *
 * <p>Reference data, not SURGE output. Features whose {@link LineType#isCrossingConstraint()} is
 * true are intended to contribute a crossing penalty to the cost surface rather than an exclusion —
 * a corridor pays to cross a highway, it does not route around the whole road network.</p>
 */
@Entity
@Table(name = "reference_lines")
public class ReferenceLine extends AuditableEntity {

    @ManyToOne(fetch = FetchType.LAZY, optional = false)
    @JoinColumn(name = "project_id", nullable = false, updatable = false)
    private Project project;

    @NotBlank
    @Size(max = 150)
    @Column(name = "external_id", nullable = false, length = 150)
    private String externalId;

    @Enumerated(EnumType.STRING)
    @Column(name = "line_type", nullable = false, length = 32)
    private LineType lineType = LineType.UNKNOWN;

    @Column(name = "crossing_cost", precision = 14, scale = 2)
    private BigDecimal crossingCost;

    @Column(name = "voltage_kv", precision = 8, scale = 2)
    private BigDecimal voltageKv;

    @Column(name = "length_m", precision = 14, scale = 2)
    private BigDecimal lengthM;

    @Size(max = 255)
    @Column(name = "source_folder", length = 255)
    private String sourceFolder;

    @Column(nullable = false, columnDefinition = "geometry(LineString, 4326)")
    private LineString path;

    protected ReferenceLine() {
    }

    public ReferenceLine(Project project, String externalId, LineType lineType, LineString path) {
        this.project = Objects.requireNonNull(project, "Project is required.");
        this.externalId = requireExternalId(externalId);
        this.lineType = lineType == null ? LineType.UNKNOWN : lineType;
        this.path = requireWgs84Path(path);
    }

    public ReferenceLine(
            Project project,
            String externalId,
            LineType lineType,
            LineString path,
            BigDecimal voltageKv,
            BigDecimal lengthM,
            String sourceFolder
    ) {
        this(project, externalId, lineType, path);
        this.voltageKv = requirePositive(voltageKv, "Voltage");
        this.lengthM = lengthM;
        this.sourceFolder = trimToNull(sourceFolder);
    }

    public Project getProject() {
        return project;
    }

    public String getExternalId() {
        return externalId;
    }

    public LineType getLineType() {
        return lineType;
    }

    public BigDecimal getCrossingCost() {
        return crossingCost;
    }

    public BigDecimal getVoltageKv() {
        return voltageKv;
    }

    public BigDecimal getLengthM() {
        return lengthM;
    }

    public String getSourceFolder() {
        return sourceFolder;
    }

    public LineString getPath() {
        return path;
    }

    private static String requireExternalId(String externalId) {
        String value = Objects.requireNonNull(externalId, "Line external ID is required.").trim();
        if (value.isEmpty()) {
            throw new IllegalArgumentException("Line external ID must not be blank.");
        }
        return value.length() > 150 ? value.substring(0, 150) : value;
    }

    private static BigDecimal requirePositive(BigDecimal value, String label) {
        if (value == null) {
            return null;
        }
        if (value.signum() <= 0) {
            throw new IllegalArgumentException(label + " must be greater than zero.");
        }
        return value;
    }

    private static LineString requireWgs84Path(LineString path) {
        LineString value = Objects.requireNonNull(path, "Line path is required.");
        if (value.getSRID() != Project.WGS84_SRID) {
            throw new IllegalArgumentException("Line path must use SRID 4326.");
        }
        if (value.getNumPoints() < 2) {
            throw new IllegalArgumentException("Line path must contain at least two vertices.");
        }
        return value;
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
}
