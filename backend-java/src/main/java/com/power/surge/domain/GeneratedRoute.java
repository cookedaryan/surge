package com.power.surge.domain;

import jakarta.persistence.Column;
import jakarta.persistence.Entity;
import jakarta.persistence.FetchType;
import jakarta.persistence.JoinColumn;
import jakarta.persistence.ManyToOne;
import jakarta.persistence.Table;
import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.NotNull;
import jakarta.validation.constraints.PositiveOrZero;
import jakarta.validation.constraints.Size;
import org.locationtech.jts.geom.LineString;
import org.locationtech.jts.geom.MultiPoint;

import java.math.BigDecimal;
import java.util.Objects;

@Entity
@Table(name = "generated_routes")
public class GeneratedRoute extends AuditableEntity {

    @ManyToOne(fetch = FetchType.LAZY, optional = false)
    @JoinColumn(name = "job_id", nullable = false, updatable = false)
    private OptimizationJob job;

    @NotBlank
    @Size(max = 100)
    @Column(name = "feeder_name", nullable = false, length = 100)
    private String feederName;

    @NotNull
    @PositiveOrZero
    @Column(name = "total_length_meters", nullable = false, precision = 12, scale = 3)
    private BigDecimal totalLengthMeters;

    @PositiveOrZero
    @Column(name = "total_cost", precision = 14, scale = 2)
    private BigDecimal totalCost;

    @PositiveOrZero
    @Column(name = "electrical_losses_kw", precision = 10, scale = 3)
    private BigDecimal electricalLossesKw;

    @Column(name = "pole_count", nullable = false)
    private Integer poleCount;

    @Column(name = "route_path", nullable = false, columnDefinition = "geometry(LineString, 4326)")
    private LineString routePath;

    @Column(name = "pole_locations", columnDefinition = "geometry(MultiPoint, 4326)")
    private MultiPoint poleLocations;

    /**
     * The Python engine's segment_id for this edge (e.g. "SEG-FDR001-0001"), used to look up the
     * real pole count via GeneratedPole.connectedRouteIds instead of the /150m estimate stored in
     * poleCount above. Null for routes created before this linkage existed, or via the manual
     * CreateRouteRequest API path that has no segment_id to supply.
     */
    @Column(name = "segment_id", length = 60)
    private String segmentId;

    protected GeneratedRoute() {
    }

    public GeneratedRoute(
            OptimizationJob job,
            String feederName,
            BigDecimal totalLengthMeters,
            BigDecimal totalCost,
            BigDecimal electricalLossesKw,
            Integer poleCount,
            LineString routePath,
            MultiPoint poleLocations,
            String segmentId
    ) {
        this.job = Objects.requireNonNull(job, "Optimization job is required.");
        this.feederName = requireFeederName(feederName);
        this.totalLengthMeters = requireNonNegative(totalLengthMeters, "Total length meters");
        this.totalCost = totalCost;
        this.electricalLossesKw = electricalLossesKw;
        this.poleCount = poleCount != null ? poleCount : 0;
        this.routePath = requireWgs84LineString(routePath);
        this.poleLocations = poleLocations != null ? requireWgs84MultiPoint(poleLocations) : null;
        this.segmentId = segmentId;
    }

    public OptimizationJob getJob() {
        return job;
    }

    public String getFeederName() {
        return feederName;
    }

    public BigDecimal getTotalLengthMeters() {
        return totalLengthMeters;
    }

    public BigDecimal getTotalCost() {
        return totalCost;
    }

    public BigDecimal getElectricalLossesKw() {
        return electricalLossesKw;
    }

    public Integer getPoleCount() {
        return poleCount;
    }

    public LineString getRoutePath() {
        return routePath;
    }

    public MultiPoint getPoleLocations() {
        return poleLocations;
    }

    public String getSegmentId() {
        return segmentId;
    }

    private static String requireFeederName(String feederName) {
        String value = Objects.requireNonNull(feederName, "Feeder name is required.").trim();
        if (value.isEmpty()) {
            throw new IllegalArgumentException("Feeder name must not be blank.");
        }
        if (value.length() > 100) {
            throw new IllegalArgumentException("Feeder name must not exceed 100 characters.");
        }
        return value;
    }

    private static BigDecimal requireNonNegative(BigDecimal value, String fieldName) {
        BigDecimal val = Objects.requireNonNull(value, fieldName + " is required.");
        if (val.signum() < 0) {
            throw new IllegalArgumentException(fieldName + " must not be negative.");
        }
        return val;
    }

    private static LineString requireWgs84LineString(LineString lineString) {
        LineString value = Objects.requireNonNull(lineString, "Route path is required.");
        if (value.getSRID() != Project.WGS84_SRID) {
            throw new IllegalArgumentException("Route path must use SRID 4326.");
        }
        return value;
    }

    private static MultiPoint requireWgs84MultiPoint(MultiPoint multiPoint) {
        if (multiPoint.getSRID() != Project.WGS84_SRID) {
            throw new IllegalArgumentException("Pole locations must use SRID 4326.");
        }
        return multiPoint;
    }
}
