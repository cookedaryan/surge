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

/**
 * An existing transmission or evacuation line structure — lattice tower, angle point or gantry.
 *
 * <p>Towers are reference assets: they are stored and rendered, but excluded from WTG grouping and
 * collector-network routing. They deliberately do not live in {@code wtg_locations}, whose
 * {@code capacity_mw NOT NULL} constraint has no meaning for a non-generating structure.</p>
 */
@Entity
@Table(name = "evacuation_towers")
public class EvacuationTower extends AuditableEntity {

    @ManyToOne(fetch = FetchType.LAZY, optional = false)
    @JoinColumn(name = "project_id", nullable = false, updatable = false)
    private Project project;

    @NotBlank
    @Size(max = 100)
    @Column(name = "external_id", nullable = false, length = 100)
    private String externalId;

    /** Free-text structure classification, e.g. {@code GANTRY}, {@code ANGLE_POINT}, {@code SUSPENSION}. */
    @Size(max = 50)
    @Column(name = "tower_type", length = 50)
    private String towerType;

    @Positive
    @Column(name = "height_m", precision = 8, scale = 2)
    private BigDecimal heightM;

    /** Line section the structure belongs to, derived from IDs such as {@code 20/12} (section 20). */
    @Size(max = 100)
    @Column(name = "line_section", length = 100)
    private String lineSection;

    /** KML folder path this asset was imported from. Retained for audit and re-classification. */
    @Size(max = 255)
    @Column(name = "source_folder", length = 255)
    private String sourceFolder;

    @Column(nullable = false, columnDefinition = "geometry(Point, 4326)")
    private Point location;

    protected EvacuationTower() {
    }

    public EvacuationTower(Project project, String externalId, Point location) {
        this.project = Objects.requireNonNull(project, "Project is required.");
        this.externalId = requireExternalId(externalId);
        this.location = requireWgs84Location(location);
    }

    public EvacuationTower(
            Project project,
            String externalId,
            Point location,
            String towerType,
            BigDecimal heightM,
            String lineSection,
            String sourceFolder
    ) {
        this(project, externalId, location);
        this.towerType = trimToNull(towerType, 50);
        this.heightM = requirePositiveHeight(heightM);
        this.lineSection = trimToNull(lineSection, 100);
        this.sourceFolder = trimToNull(sourceFolder, 255);
    }

    public Project getProject() {
        return project;
    }

    public String getExternalId() {
        return externalId;
    }

    public String getTowerType() {
        return towerType;
    }

    public BigDecimal getHeightM() {
        return heightM;
    }

    public String getLineSection() {
        return lineSection;
    }

    public String getSourceFolder() {
        return sourceFolder;
    }

    public Point getLocation() {
        return location;
    }

    private static String requireExternalId(String externalId) {
        String value = Objects.requireNonNull(externalId, "Tower external ID is required.").trim();
        if (value.isEmpty()) {
            throw new IllegalArgumentException("Tower external ID must not be blank.");
        }
        if (value.length() > 100) {
            throw new IllegalArgumentException("Tower external ID must not exceed 100 characters.");
        }
        return value;
    }

    private static BigDecimal requirePositiveHeight(BigDecimal heightM) {
        if (heightM == null) {
            return null;
        }
        if (heightM.signum() <= 0) {
            throw new IllegalArgumentException("Tower height must be greater than zero.");
        }
        return heightM;
    }

    private static Point requireWgs84Location(Point location) {
        Point value = Objects.requireNonNull(location, "Tower location is required.");
        if (value.getSRID() != Project.WGS84_SRID) {
            throw new IllegalArgumentException("Tower location must use SRID 4326.");
        }
        return value;
    }

    private static String trimToNull(String value, int maxLength) {
        if (value == null) {
            return null;
        }
        String trimmed = value.trim();
        if (trimmed.isEmpty()) {
            return null;
        }
        return trimmed.length() > maxLength ? trimmed.substring(0, maxLength) : trimmed;
    }
}
