package com.power.surge.domain;

import org.junit.jupiter.api.Test;
import org.locationtech.jts.geom.Coordinate;
import org.locationtech.jts.geom.GeometryFactory;
import org.locationtech.jts.geom.LineString;
import org.locationtech.jts.geom.LinearRing;
import org.locationtech.jts.geom.Polygon;
import org.locationtech.jts.geom.PrecisionModel;

import java.math.BigDecimal;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatIllegalArgumentException;

class OptimizationDomainTest {

    private final GeometryFactory wgs84GeometryFactory = new GeometryFactory(
            new PrecisionModel(),
            Project.WGS84_SRID
    );

    @Test
    void createsOptimizationJobWithDefaults() {
        Project project = new Project("Ridge Farm", "Test");
        OptimizationJob job = new OptimizationJob(project, null, null, null, null, null);

        assertThat(job.getProject()).isSameAs(project);
        assertThat(job.getStatus()).isEqualTo(JobStatus.PENDING);
        assertThat(job.getAlgorithmType()).isEqualTo("MULTI_OBJECTIVE_A_STAR");
        assertThat(job.getCapexWeight()).isEqualTo(new BigDecimal("0.5000"));
        assertThat(job.getLossesWeight()).isEqualTo(new BigDecimal("0.5000"));
        assertThat(job.getMaxSpanMeters()).isEqualTo(new BigDecimal("150.00"));
        assertThat(job.getVoltageKv()).isEqualTo(new BigDecimal("33.00"));
    }

    @Test
    void updatesOptimizationJobLifecycleState() {
        Project project = new Project("Ridge Farm", "Test");
        OptimizationJob job = new OptimizationJob(project, "A_STAR", null, null, null, null);

        job.markRunning();
        assertThat(job.getStatus()).isEqualTo(JobStatus.RUNNING);
        assertThat(job.getStartedAt()).isNotNull();

        job.markCompleted("{\"total_cost\": 150000.00}");
        assertThat(job.getStatus()).isEqualTo(JobStatus.COMPLETED);
        assertThat(job.getCompletedAt()).isNotNull();
        assertThat(job.getResultSummaryJson()).contains("150000.00");
    }

    @Test
    void createsGeneratedRouteWithValidWgs84Path() {
        Project project = new Project("Ridge Farm", "Test");
        OptimizationJob job = new OptimizationJob(project, "A_STAR", null, null, null, null);

        Coordinate[] coords = new Coordinate[]{
                new Coordinate(77.2300, 28.6300),
                new Coordinate(77.2400, 28.6400)
        };
        LineString path = wgs84GeometryFactory.createLineString(coords);

        GeneratedRoute route = new GeneratedRoute(
                job,
                "Feeder 1",
                new BigDecimal("1414.21"),
                new BigDecimal("50000.00"),
                new BigDecimal("12.50"),
                10,
                path,
                null,
                null
        );

        assertThat(route.getJob()).isSameAs(job);
        assertThat(route.getFeederName()).isEqualTo("Feeder 1");
        assertThat(route.getRoutePath().getSRID()).isEqualTo(Project.WGS84_SRID);
    }

    @Test
    void createsRestrictedAreaAndCadastralParcel() {
        Project project = new Project("Ridge Farm", "Test");

        Coordinate[] ringCoords = new Coordinate[]{
                new Coordinate(77.23, 28.63),
                new Coordinate(77.24, 28.63),
                new Coordinate(77.24, 28.64),
                new Coordinate(77.23, 28.64),
                new Coordinate(77.23, 28.63)
        };
        LinearRing ring = wgs84GeometryFactory.createLinearRing(ringCoords);
        Polygon polygon = wgs84GeometryFactory.createPolygon(ring);

        RestrictedArea area = new RestrictedArea(project, "Forest Reserve", "FOREST", new BigDecimal("50.0"), polygon);
        CadastralParcel parcel = new CadastralParcel(project, "P-101", "John Doe", new BigDecimal("12.50"), polygon);

        assertThat(area.getName()).isEqualTo("Forest Reserve");
        assertThat(area.getGeometry().getSRID()).isEqualTo(Project.WGS84_SRID);
        assertThat(parcel.getParcelId()).isEqualTo("P-101");
        assertThat(parcel.getAcquisitionCostPerM2()).isEqualTo(new BigDecimal("12.50"));
    }

    @Test
    void rejectsInvalidGeometrySrid() {
        Project project = new Project("Ridge Farm", "Test");
        LineString missingSrid = new GeometryFactory().createLineString(new Coordinate[]{
                new Coordinate(77.23, 28.63),
                new Coordinate(77.24, 28.64)
        });

        OptimizationJob job = new OptimizationJob(project, "A_STAR", null, null, null, null);

        assertThatIllegalArgumentException().isThrownBy(() -> new GeneratedRoute(
                job,
                "Feeder 1",
                new BigDecimal("1000"),
                null,
                null,
                5,
                missingSrid,
                null,
                null
        )).withMessage("Route path must use SRID 4326.");
    }
}
