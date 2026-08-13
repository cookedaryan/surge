package com.power.surge.domain;

import jakarta.persistence.Column;
import jakarta.persistence.Entity;
import jakarta.persistence.FetchType;
import jakarta.persistence.JoinColumn;
import jakarta.persistence.ManyToOne;
import jakarta.persistence.Table;
import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.Size;
import org.hibernate.annotations.JdbcTypeCode;
import org.hibernate.type.SqlTypes;
import org.locationtech.jts.geom.Point;

import java.util.List;
import java.util.Objects;

@Entity
@Table(name = "generated_poles")
public class GeneratedPole extends AuditableEntity {

    @ManyToOne(fetch = FetchType.LAZY, optional = false)
    @JoinColumn(name = "job_id", nullable = false, updatable = false)
    private OptimizationJob job;

    @NotBlank
    @Size(max = 150)
    @Column(name = "pole_identifier", nullable = false, length = 150)
    private String poleIdentifier;

    @Column(name = "feeder_name", length = 100)
    private String feederName;

    @Column(name = "pole_role", length = 30)
    private String poleRole;

    @Column(name = "recommended_pole_type", length = 100)
    private String recommendedPoleType;

    @JdbcTypeCode(SqlTypes.ARRAY)
    @Column(name = "connected_feeder_ids", columnDefinition = "text[]")
    private List<String> connectedFeederIds;

    /**
     * The Python engine's segment_id(s) (pnc_segment.segment_id) this pole sits on — one for most
     * poles, more than one for a shared junction pole where two route edges meet. Matches
     * GeneratedRoute.segmentId, letting a route's real pole count be counted instead of estimated.
     */
    @JdbcTypeCode(SqlTypes.ARRAY)
    @Column(name = "connected_route_ids", columnDefinition = "text[]")
    private List<String> connectedRouteIds;

    @Column(name = "location", nullable = false, columnDefinition = "geometry(Point, 4326)")
    private Point location;

    protected GeneratedPole() {
    }

    public GeneratedPole(
            OptimizationJob job,
            String poleIdentifier,
            String feederName,
            String poleRole,
            String recommendedPoleType,
            List<String> connectedFeederIds,
            List<String> connectedRouteIds,
            Point location
    ) {
        this.job = Objects.requireNonNull(job, "Optimization job is required.");
        this.poleIdentifier = requirePoleIdentifier(poleIdentifier);
        this.feederName = feederName;
        this.poleRole = poleRole;
        this.recommendedPoleType = recommendedPoleType;
        this.connectedFeederIds = connectedFeederIds;
        this.connectedRouteIds = connectedRouteIds;
        this.location = requireWgs84Point(location);
    }

    public OptimizationJob getJob() {
        return job;
    }

    public String getPoleIdentifier() {
        return poleIdentifier;
    }

    public String getFeederName() {
        return feederName;
    }

    public String getPoleRole() {
        return poleRole;
    }

    public String getRecommendedPoleType() {
        return recommendedPoleType;
    }

    public List<String> getConnectedFeederIds() {
        return connectedFeederIds;
    }

    public List<String> getConnectedRouteIds() {
        return connectedRouteIds;
    }

    public Point getLocation() {
        return location;
    }

    private static String requirePoleIdentifier(String poleIdentifier) {
        String value = Objects.requireNonNull(poleIdentifier, "Pole identifier is required.").trim();
        if (value.isEmpty()) {
            throw new IllegalArgumentException("Pole identifier must not be blank.");
        }
        if (value.length() > 150) {
            throw new IllegalArgumentException("Pole identifier must not exceed 150 characters.");
        }
        return value;
    }

    private static Point requireWgs84Point(Point point) {
        Point value = Objects.requireNonNull(point, "Pole location is required.");
        if (value.getSRID() != Project.WGS84_SRID) {
            throw new IllegalArgumentException("Pole location must use SRID 4326.");
        }
        return value;
    }
}
