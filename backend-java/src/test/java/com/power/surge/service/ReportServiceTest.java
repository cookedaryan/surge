package com.power.surge.service;

import com.power.surge.domain.CadastralParcel;
import com.power.surge.domain.GeneratedPole;
import com.power.surge.domain.GeneratedRoute;
import com.power.surge.domain.JobStatus;
import com.power.surge.domain.OptimizationJob;
import com.power.surge.domain.Project;
import com.power.surge.dto.report.EngineeringBomReportResponse;
import com.power.surge.dto.report.FeederBomSummary;
import com.power.surge.dto.report.ParcelImpactSummary;
import com.power.surge.dto.report.PoleScheduleEntry;
import com.power.surge.dto.report.RouteSegmentDetail;
import com.power.surge.repository.CadastralParcelRepository;
import com.power.surge.repository.GeneratedPoleRepository;
import com.power.surge.repository.GeneratedRouteRepository;
import com.power.surge.repository.OptimizationJobRepository;
import com.power.surge.repository.ProjectRepository;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.locationtech.jts.geom.Coordinate;
import org.locationtech.jts.geom.GeometryFactory;
import org.locationtech.jts.geom.LineString;
import org.locationtech.jts.geom.LinearRing;
import org.locationtech.jts.geom.Polygon;
import org.locationtech.jts.geom.PrecisionModel;
import org.mockito.Mock;
import org.mockito.junit.jupiter.MockitoExtension;

import java.math.BigDecimal;
import java.util.List;
import java.util.Optional;
import java.util.UUID;

import static org.assertj.core.api.Assertions.assertThat;
import static org.mockito.ArgumentMatchers.anyDouble;
import static org.mockito.ArgumentMatchers.eq;
import static org.mockito.Mockito.when;

@ExtendWith(MockitoExtension.class)
class ReportServiceTest {

    @Mock
    private ProjectRepository projectRepository;

    @Mock
    private OptimizationJobRepository jobRepository;

    @Mock
    private GeneratedRouteRepository routeRepository;

    @Mock
    private GeneratedPoleRepository poleRepository;

    @Mock
    private CadastralParcelRepository parcelRepository;

    @Mock
    private AuditLogService auditLogService;

    @Mock
    private CableCatalogueService cableCatalogueService;

    private ReportService reportService;
    private final GeometryFactory geometryFactory = new GeometryFactory(new PrecisionModel(), Project.WGS84_SRID);

    @BeforeEach
    void setUp() {
        reportService = new ReportService(projectRepository, jobRepository, routeRepository, poleRepository, parcelRepository, auditLogService, cableCatalogueService);
    }

    @Test
    void generateBomReport_success() {
        UUID projectId = UUID.randomUUID();
        UUID jobId = UUID.randomUUID();

        Project project = new Project("Test Project", "Description");
        org.springframework.test.util.ReflectionTestUtils.setField(project, "id", projectId);
        OptimizationJob job = new OptimizationJob(project, "MULTI_OBJECTIVE_A_STAR", null, null, null, null);
        org.springframework.test.util.ReflectionTestUtils.setField(job, "id", jobId);

        LineString lineString = geometryFactory.createLineString(new Coordinate[]{
                new Coordinate(77.23, 28.63),
                new Coordinate(77.25, 28.64)
        });
        GeneratedRoute route = new GeneratedRoute(
                job, "Feeder-01", new BigDecimal("2500.00"), null, new BigDecimal("12.5"), 15, lineString, null, null
        );
        // Network capex comes from the engine's own figure on the job, not from summing per-route
        // numbers: conductor is the only component attributed to a route, so a sum of routes would
        // omit poles and land and present the remainder as a total.
        job.applyCost("INR", new BigDecimal("100000.00"), new BigDecimal("50000.00"), BigDecimal.ZERO,
                new BigDecimal("150000.00"), new BigDecimal("10.0000"), new BigDecimal("35000.00"),
                new BigDecimal("300000.00"), new BigDecimal("450000.00"),
                "IN-33KV-INDICATIVE", "2026.1", "2026-01-01", 0);

        LinearRing ring = geometryFactory.createLinearRing(new Coordinate[]{
                new Coordinate(77.20, 28.60),
                new Coordinate(77.21, 28.60),
                new Coordinate(77.21, 28.61),
                new Coordinate(77.20, 28.60)
        });
        Polygon polygon = geometryFactory.createPolygon(ring);
        CadastralParcel parcel = new CadastralParcel(project, "P-001", "John Doe", new BigDecimal("100.00"), polygon);

        when(projectRepository.findById(projectId)).thenReturn(Optional.of(project));
        when(jobRepository.findById(jobId)).thenReturn(Optional.of(job));
        when(routeRepository.findAllByJobIdOrderByFeederNameAsc(jobId)).thenReturn(List.of(route));
        when(poleRepository.findAllByJobIdOrderByPoleIdentifierAsc(jobId)).thenReturn(List.of());
        when(parcelRepository.findAllByProjectIdOrderByParcelIdAsc(projectId)).thenReturn(List.of(parcel));

        EngineeringBomReportResponse report = reportService.generateBomReport(projectId, jobId);

        assertThat(report).isNotNull();
        assertThat(report.projectName()).isEqualTo("Test Project");
        assertThat(report.totalFeeders()).isEqualTo(1);
        assertThat(report.totalPoles()).isEqualTo(15);
        assertThat(report.feederSummaries()).hasSize(1);
        assertThat(report.parcelImpactSummaries()).hasSize(1);
    }

    /**
     * Land compensation is money, and it used to be derived from the parcel's entire area scaled by
     * an unexplained constant. It must come from the right-of-way corridor overlap instead.
     */
    @Test
    void parcelImpactUsesTheRightOfWayOverlapRatherThanTheWholeParcel() {
        UUID projectId = UUID.randomUUID();
        UUID jobId = UUID.randomUUID();

        Project project = new Project("Test Project", "Description");
        org.springframework.test.util.ReflectionTestUtils.setField(project, "id", projectId);
        OptimizationJob job = new OptimizationJob(project, "MULTI_OBJECTIVE_A_STAR", null, null, null, null);
        org.springframework.test.util.ReflectionTestUtils.setField(job, "id", jobId);

        // A large parcel whose corridor overlap is only a narrow strip.
        LinearRing ring = geometryFactory.createLinearRing(new Coordinate[]{
                new Coordinate(77.20, 28.60),
                new Coordinate(77.30, 28.60),
                new Coordinate(77.30, 28.70),
                new Coordinate(77.20, 28.70),
                new Coordinate(77.20, 28.60)
        });
        CadastralParcel parcel = new CadastralParcel(
                project, "P-001", "John Doe", new BigDecimal("2.00"), geometryFactory.createPolygon(ring));

        when(projectRepository.findById(projectId)).thenReturn(Optional.of(project));
        when(jobRepository.findById(jobId)).thenReturn(Optional.of(job));
        when(routeRepository.findAllByJobIdOrderByFeederNameAsc(jobId)).thenReturn(List.of());
        when(poleRepository.findAllByJobIdOrderByPoleIdentifierAsc(jobId)).thenReturn(List.of());
        when(parcelRepository.findAllByProjectIdOrderByParcelIdAsc(projectId)).thenReturn(List.of(parcel));
        when(parcelRepository.findRowCorridorAreaByParcel(eq(projectId), eq(jobId), anyDouble()))
                .thenReturn(List.<Object[]>of(new Object[]{"P-001", 1500.0}));

        EngineeringBomReportResponse report = reportService.generateBomReport(projectId, jobId);

        ParcelImpactSummary summary = report.parcelImpactSummaries().get(0);
        assertThat(summary.affectedAreaM2()).isEqualTo(1500.0);
        // 1500 m2 at $2.00/m2 — derived from the corridor overlap, not the parcel's full extent.
        assertThat(summary.estimatedCompensationCost()).isEqualByComparingTo(new BigDecimal("3000.00"));
    }

    /** A spatial failure must not invent an area that would feed a compensation figure. */
    @Test
    void parcelImpactReportsZeroWhenTheCorridorOverlapCannotBeComputed() {
        UUID projectId = UUID.randomUUID();
        UUID jobId = UUID.randomUUID();

        Project project = new Project("Test Project", "Description");
        org.springframework.test.util.ReflectionTestUtils.setField(project, "id", projectId);
        OptimizationJob job = new OptimizationJob(project, "MULTI_OBJECTIVE_A_STAR", null, null, null, null);
        org.springframework.test.util.ReflectionTestUtils.setField(job, "id", jobId);

        LinearRing ring = geometryFactory.createLinearRing(new Coordinate[]{
                new Coordinate(77.20, 28.60),
                new Coordinate(77.21, 28.60),
                new Coordinate(77.21, 28.61),
                new Coordinate(77.20, 28.60)
        });
        CadastralParcel parcel = new CadastralParcel(
                project, "P-001", "John Doe", new BigDecimal("100.00"), geometryFactory.createPolygon(ring));

        when(projectRepository.findById(projectId)).thenReturn(Optional.of(project));
        when(jobRepository.findById(jobId)).thenReturn(Optional.of(job));
        when(routeRepository.findAllByJobIdOrderByFeederNameAsc(jobId)).thenReturn(List.of());
        when(poleRepository.findAllByJobIdOrderByPoleIdentifierAsc(jobId)).thenReturn(List.of());
        when(parcelRepository.findAllByProjectIdOrderByParcelIdAsc(projectId)).thenReturn(List.of(parcel));
        when(parcelRepository.findRowCorridorAreaByParcel(eq(projectId), eq(jobId), anyDouble()))
                .thenThrow(new org.springframework.dao.InvalidDataAccessResourceUsageException("no postgis"));

        EngineeringBomReportResponse report = reportService.generateBomReport(projectId, jobId);

        assertThat(report.parcelImpactSummaries().get(0).affectedAreaM2()).isZero();
        assertThat(report.parcelImpactSummaries().get(0).estimatedCompensationCost())
                .isEqualByComparingTo(BigDecimal.ZERO);
    }

    /**
     * An uncosted run must read as uncosted.
     *
     * <p>Every money figure in the exports came from a per-route {@code length × 80} fabrication, so
     * a run with no cost catalogue still produced a full set of confident numbers. Removing the
     * fabrication is only half the fix: printing 0 instead would turn "nobody priced this" into
     * "this is free", which is worse, because a zero looks like an answer.
     */
    @Test
    void generateBomCsv_saysNotCostedRatherThanZeroWhenNothingWasPriced() {
        UUID projectId = UUID.randomUUID();
        UUID jobId = UUID.randomUUID();
        Fixture f = fixture(projectId, jobId);

        when(routeRepository.findAllByJobIdOrderByFeederNameAsc(jobId)).thenReturn(List.of(
                segment(f.job(), "FDR-001", "S1", "1000.00", null, "1.0")));
        when(poleRepository.findAllByJobIdOrderByPoleIdentifierAsc(jobId)).thenReturn(List.of());
        when(parcelRepository.findAllByProjectIdOrderByParcelIdAsc(projectId)).thenReturn(List.of());

        String csv = reportService.generateBomCsv(projectId, jobId);

        assertThat(csv).contains("Estimated capex,Not costed");
        // The column heading must not promise a total it is not carrying: conductor is the only
        // component the engine attributes to a route.
        assertThat(csv).contains("Conductor Cost");
        assertThat(csv).doesNotContain("Total Cost ($)");
        // No currency symbol is invented where no catalogue named one.
        assertThat(csv).doesNotContain("capex ($)");
        // And the feeder row itself: a roll-up of nothing is not zero. Summing an all-null column
        // from BigDecimal.ZERO would print 0.000 here, which reads as a feeder that costs nothing.
        assertThat(csv).contains("FDR-001,1,1000.000,0,Not costed,1.000");
        // And the totals row, which appended the BigDecimal directly and so printed the
        // literal string "null" once the figure could be absent.
        assertThat(csv).doesNotContain(",null,");
    }

    /** With a catalogue, the figures appear under the currency they were priced in. */
    @Test
    void generateBomCsv_namesTheCurrencyTheRunWasPricedIn() {
        UUID projectId = UUID.randomUUID();
        UUID jobId = UUID.randomUUID();
        Fixture f = fixture(projectId, jobId);
        f.job().applyCost("INR", new BigDecimal("208393.79"), new BigDecimal("188000.00"),
                BigDecimal.ZERO, new BigDecimal("396393.79"), new BigDecimal("16.4264"),
                new BigDecimal("57492.50"), new BigDecimal("613719.60"), new BigDecimal("1010113.38"),
                "IN-33KV-INDICATIVE", "2026.1", "2026-01-01", 0);

        when(routeRepository.findAllByJobIdOrderByFeederNameAsc(jobId)).thenReturn(List.of(
                segment(f.job(), "FDR-001", "S1", "1000.00", "104196.89", "1.0")));
        when(poleRepository.findAllByJobIdOrderByPoleIdentifierAsc(jobId)).thenReturn(List.of());
        when(parcelRepository.findAllByProjectIdOrderByParcelIdAsc(projectId)).thenReturn(List.of());

        String csv = reportService.generateBomCsv(projectId, jobId);

        assertThat(csv).contains("Estimated capex (INR),396393.79");
        assertThat(csv).contains("Conductor Cost (INR)");
        assertThat(csv).contains("104196.89");
    }

    /**
     * A partial sum has to be labelled as one.
     *
     * <p>The engine omits a component it could not price rather than pricing it at zero, so a capex
     * with failures behind it is not the network's cost — and a reader has no way to know that from
     * the number.
     */
    @Test
    void generateBomCsv_flagsCapexThatIsMissingComponents() {
        UUID projectId = UUID.randomUUID();
        UUID jobId = UUID.randomUUID();
        Fixture f = fixture(projectId, jobId);
        f.job().applyCost("INR", null, new BigDecimal("188000.00"), BigDecimal.ZERO,
                new BigDecimal("188000.00"), null, null, null, null,
                "IN-33KV-INDICATIVE", "2026.1", "2026-01-01", 1);

        when(routeRepository.findAllByJobIdOrderByFeederNameAsc(jobId)).thenReturn(List.of(
                segment(f.job(), "FDR-001", "S1", "1000.00", null, "1.0")));
        when(poleRepository.findAllByJobIdOrderByPoleIdentifierAsc(jobId)).thenReturn(List.of());
        when(parcelRepository.findAllByProjectIdOrderByParcelIdAsc(projectId)).thenReturn(List.of());

        String csv = reportService.generateBomCsv(projectId, jobId);

        assertThat(csv).contains("Cost components not priced,1 (capex above is incomplete)");
    }

    @Test
    void generateBomCsv_success() {
        UUID projectId = UUID.randomUUID();
        UUID jobId = UUID.randomUUID();

        Project project = new Project("Test Project", "Description");
        org.springframework.test.util.ReflectionTestUtils.setField(project, "id", projectId);
        OptimizationJob job = new OptimizationJob(project, "MULTI_OBJECTIVE_A_STAR", null, null, null, null);
        org.springframework.test.util.ReflectionTestUtils.setField(job, "id", jobId);

        LineString lineString = geometryFactory.createLineString(new Coordinate[]{
                new Coordinate(77.23, 28.63),
                new Coordinate(77.25, 28.64)
        });
        GeneratedRoute route = new GeneratedRoute(
                job, "Feeder-01", new BigDecimal("2500.00"), new BigDecimal("150000.00"), new BigDecimal("12.5"), 15, lineString, null, null
        );

        when(projectRepository.findById(projectId)).thenReturn(Optional.of(project));
        when(jobRepository.findById(jobId)).thenReturn(Optional.of(job));
        when(routeRepository.findAllByJobIdOrderByFeederNameAsc(jobId)).thenReturn(List.of(route));
        when(poleRepository.findAllByJobIdOrderByPoleIdentifierAsc(jobId)).thenReturn(List.of());
        when(parcelRepository.findAllByProjectIdOrderByParcelIdAsc(projectId)).thenReturn(List.of());

        String csv = reportService.generateBomCsv(projectId, jobId);

        assertThat(csv).contains("SURGE Engineering Bill of Materials");
        assertThat(csv).contains("Feeder-01");
        assertThat(csv).contains("2500.00");

        // Every section a crew or a reviewer needs must be present, not just the feeder roll-up.
        assertThat(csv)
                .contains("--- RUN PARAMETERS ---")
                .contains("--- NETWORK TOTALS ---")
                .contains("--- POLE COUNT BY STRUCTURAL ROLE ---")
                .contains("--- POLE COUNT BY RECOMMENDED TYPE ---")
                .contains("--- FEEDER SUMMARY ---")
                .contains("--- ROUTE SEGMENT SCHEDULE ---")
                .contains("--- POLE SETTING-OUT SCHEDULE ---")
                .contains("--- CADASTRAL PARCEL IMPACT & COMPENSATION ---");

        // Segment endpoints come from the route geometry, at full coordinate precision.
        assertThat(csv).contains("28.630000,77.230000,28.640000,77.250000");
        assertThat(csv).contains("LINESTRING");
    }

    @Test
    void getScenarioComparison_omitsScenariosThatWereNeverRun() {
        UUID projectId = UUID.randomUUID();
        Project project = new Project("Test Project", "Description");

        when(projectRepository.findById(projectId)).thenReturn(Optional.of(project));
        when(jobRepository.findAllByProjectIdOrderByCreatedAtDesc(projectId)).thenReturn(List.of());

        com.power.surge.dto.report.ScenarioComparisonResponse resp = reportService.getScenarioComparison(projectId);

        assertThat(resp).isNotNull();
        assertThat(resp.scenarios()).isEmpty();
    }

    @Test
    void getScenarioComparison_reflectsTheRealCompletedJobForThatScenario() {
        UUID projectId = UUID.randomUUID();
        UUID jobId = UUID.randomUUID();

        Project project = new Project("Test Project", "Description");
        org.springframework.test.util.ReflectionTestUtils.setField(project, "id", projectId);
        OptimizationJob job = new OptimizationJob(project, "MULTI_OBJECTIVE_A_STAR", "Minimum Cost", null, null, null, null);
        org.springframework.test.util.ReflectionTestUtils.setField(job, "id", jobId);
        job.markCompleted("{}");

        LineString lineString = geometryFactory.createLineString(new Coordinate[]{
                new Coordinate(77.23, 28.63),
                new Coordinate(77.25, 28.64)
        });
        GeneratedRoute route = new GeneratedRoute(
                job, "Feeder-01", new BigDecimal("2500.00"), null, new BigDecimal("12.5"), 15, lineString, null, null
        );
        // The comparison reports the engine's own network capex from the job. It used to sum a
        // per-route length x 80 fabrication.
        job.applyCost("INR", new BigDecimal("100000.00"), new BigDecimal("50000.00"), BigDecimal.ZERO,
                new BigDecimal("150000.00"), new BigDecimal("10.0000"), new BigDecimal("35000.00"),
                new BigDecimal("300000.00"), new BigDecimal("450000.00"),
                "IN-33KV-INDICATIVE", "2026.1", "2026-01-01", 0);

        when(projectRepository.findById(projectId)).thenReturn(Optional.of(project));
        when(jobRepository.findAllByProjectIdOrderByCreatedAtDesc(projectId)).thenReturn(List.of(job));
        when(jobRepository.findById(jobId)).thenReturn(Optional.of(job));
        when(routeRepository.findAllByJobIdOrderByFeederNameAsc(jobId)).thenReturn(List.of(route));
        when(poleRepository.findAllByJobIdOrderByPoleIdentifierAsc(jobId)).thenReturn(List.of());
        when(parcelRepository.findAllByProjectIdOrderByParcelIdAsc(projectId)).thenReturn(List.of());

        com.power.surge.dto.report.ScenarioComparisonResponse resp = reportService.getScenarioComparison(projectId);

        assertThat(resp.scenarios()).hasSize(1);
        assertThat(resp.scenarios().get(0).scenarioName()).isEqualTo("Minimum Cost");
        assertThat(resp.scenarios().get(0).jobId()).isEqualTo(jobId);
        assertThat(resp.scenarios().get(0).totalEstimatedCost()).isEqualTo(150000.00);
        assertThat(resp.scenarios().get(0).totalPoles()).isEqualTo(15);
    }

    /**
     * A feeder is built from several segments — seven feeders span 38 segments on the reference
     * project. The report used to emit one row per segment while calling them feeders, and count
     * route rows as the feeder total, so that project reported 38 feeders.
     */
    @Test
    void feederSummariesRollUpSegmentsRatherThanListingEachOne() {
        UUID projectId = UUID.randomUUID();
        UUID jobId = UUID.randomUUID();
        Fixture f = fixture(projectId, jobId);

        when(routeRepository.findAllByJobIdOrderByFeederNameAsc(jobId)).thenReturn(List.of(
                segment(f.job(), "FDR-001", "S1", "1000.00", "10000.00", "1.0"),
                segment(f.job(), "FDR-001", "S2", "2000.00", "20000.00", "2.0"),
                segment(f.job(), "FDR-002", "S3", "3000.00", "30000.00", "3.0")
        ));
        when(poleRepository.findAllByJobIdOrderByPoleIdentifierAsc(jobId)).thenReturn(List.of());
        when(parcelRepository.findAllByProjectIdOrderByParcelIdAsc(projectId)).thenReturn(List.of());

        EngineeringBomReportResponse report = reportService.generateBomReport(projectId, jobId);

        assertThat(report.totalFeeders()).isEqualTo(2);
        assertThat(report.totalSegments()).isEqualTo(3);
        assertThat(report.feederSummaries()).hasSize(2);
        assertThat(report.segmentDetails()).hasSize(3);

        FeederBomSummary first = report.feederSummaries().get(0);
        assertThat(first.feederName()).isEqualTo("FDR-001");
        assertThat(first.segmentCount()).isEqualTo(2);
        assertThat(first.lengthMeters()).isEqualByComparingTo("3000.00");
        assertThat(first.conductorCost()).isEqualByComparingTo("30000.00");
        assertThat(first.electricalLossesKw()).isEqualByComparingTo("3.0");
    }

    /** Coordinates are what make the schedule usable for setting out on the ground. */
    @Test
    void reportCarriesPoleTypesAndCoordinates() {
        UUID projectId = UUID.randomUUID();
        UUID jobId = UUID.randomUUID();
        Fixture f = fixture(projectId, jobId);

        GeneratedPole angle = new GeneratedPole(f.job(), "P-001", "FDR-001", "angle", "PSC-11M",
                List.of("FDR-001"), List.of("S1"), geometryFactory.createPoint(new Coordinate(77.234567, 28.634567)));
        GeneratedPole tangent = new GeneratedPole(f.job(), "P-002", "FDR-001", "tangent", "PSC-9M",
                List.of("FDR-001"), List.of("S1"), geometryFactory.createPoint(new Coordinate(77.24, 28.64)));

        when(routeRepository.findAllByJobIdOrderByFeederNameAsc(jobId)).thenReturn(List.of(
                segment(f.job(), "FDR-001", "S1", "1000.00", "10000.00", "1.0")));
        when(poleRepository.findAllByJobIdOrderByPoleIdentifierAsc(jobId)).thenReturn(List.of(angle, tangent));
        when(parcelRepository.findAllByProjectIdOrderByParcelIdAsc(projectId)).thenReturn(List.of());

        EngineeringBomReportResponse report = reportService.generateBomReport(projectId, jobId);

        assertThat(report.poleSchedule()).hasSize(2);
        PoleScheduleEntry entry = report.poleSchedule().get(0);
        assertThat(entry.poleIdentifier()).isEqualTo("P-001");
        assertThat(entry.role()).isEqualTo("angle");
        assertThat(entry.recommendedPoleType()).isEqualTo("PSC-11M");
        assertThat(entry.latitude()).isEqualTo(28.634567);
        assertThat(entry.longitude()).isEqualTo(77.234567);
        assertThat(entry.connectedSegments()).isEqualTo("S1");

        assertThat(report.poleCountByRole()).containsEntry("angle", 1).containsEntry("tangent", 1);
        assertThat(report.poleCountByType()).containsEntry("PSC-11M", 1).containsEntry("PSC-9M", 1);

        RouteSegmentDetail seg = report.segmentDetails().get(0);
        assertThat(seg.startLatitude()).isEqualTo(28.63);
        assertThat(seg.startLongitude()).isEqualTo(77.23);
        assertThat(seg.endLatitude()).isEqualTo(28.64);
        assertThat(seg.vertexCount()).isEqualTo(2);
        assertThat(seg.pathWkt()).startsWith("LINESTRING");
    }

    /** The inputs have to travel with the figures, or the figures cannot be reproduced. */
    @Test
    void reportCarriesTheRunParameters() {
        UUID projectId = UUID.randomUUID();
        UUID jobId = UUID.randomUUID();

        Project project = new Project("Test Project", "Description");
        org.springframework.test.util.ReflectionTestUtils.setField(project, "id", projectId);
        OptimizationJob job = new OptimizationJob(
                project, "MULTI_OBJECTIVE_A_STAR", "Minimum Land Impact",
                new BigDecimal("0.40"), new BigDecimal("0.25"), new BigDecimal("180.00"),
                new BigDecimal("66.00"), new BigDecimal("12.500"), new BigDecimal("4.50"),
                new BigDecimal("22.00"));
        org.springframework.test.util.ReflectionTestUtils.setField(job, "id", jobId);

        when(projectRepository.findById(projectId)).thenReturn(Optional.of(project));
        when(jobRepository.findById(jobId)).thenReturn(Optional.of(job));
        when(routeRepository.findAllByJobIdOrderByFeederNameAsc(jobId)).thenReturn(List.of());
        when(poleRepository.findAllByJobIdOrderByPoleIdentifierAsc(jobId)).thenReturn(List.of());
        when(parcelRepository.findAllByProjectIdOrderByParcelIdAsc(projectId)).thenReturn(List.of());

        EngineeringBomReportResponse report = reportService.generateBomReport(projectId, jobId);

        assertThat(report.runParameters()).isNotNull();
        assertThat(report.runParameters().scenario()).isEqualTo("Minimum Land Impact");
        assertThat(report.runParameters().algorithmType()).isEqualTo("MULTI_OBJECTIVE_A_STAR");
        assertThat(report.runParameters().voltageKv()).isEqualByComparingTo("66.00");
        assertThat(report.runParameters().feederCapacityMw()).isEqualByComparingTo("12.500");
        assertThat(report.runParameters().maxSpanMeters()).isEqualByComparingTo("180.00");
        // The ROW width the run actually used, not the service's fallback constant.
        assertThat(report.rowWidthMeters()).isEqualByComparingTo("22.00");
    }

    /**
     * Conductor is the largest material cost in a collector network. A bill of materials that
     * names every pole but not the cable between them cannot be priced.
     */
    @Test
    void theReportNamesTheConductorChosenForEachSegment() {
        UUID projectId = UUID.randomUUID();
        UUID jobId = UUID.randomUUID();
        Fixture f = fixture(projectId, jobId);

        GeneratedRoute sized = segment(f.job(), "FDR-001", "S1", "1000.00", "10000.00", "1.0");
        sized.applyCableSelection("AL-240", new BigDecimal("210.50"),
                new BigDecimal("400.00"), new BigDecimal("52.60"));
        GeneratedRoute unsized = segment(f.job(), "FDR-001", "S2", "500.00", "5000.00", "0.5");

        when(routeRepository.findAllByJobIdOrderByFeederNameAsc(jobId))
                .thenReturn(List.of(sized, unsized));
        when(poleRepository.findAllByJobIdOrderByPoleIdentifierAsc(jobId)).thenReturn(List.of());
        when(parcelRepository.findAllByProjectIdOrderByParcelIdAsc(projectId)).thenReturn(List.of());

        EngineeringBomReportResponse report = reportService.generateBomReport(projectId, jobId);

        RouteSegmentDetail first = report.segmentDetails().get(0);
        assertThat(first.cableTypeId()).isEqualTo("AL-240");
        assertThat(first.cableUtilisationPct()).isEqualByComparingTo("52.60");
        // A segment with no reported conductor stays empty rather than inheriting a neighbour's.
        assertThat(report.segmentDetails().get(1).cableTypeId()).isNull();
    }

    /** Procurement orders by conductor type, so the lengths have to be totalled by type. */
    @Test
    void conductorTotalsGroupByTypeAndKeepUnreportedSegmentsVisible() {
        List<RouteSegmentDetail> segments = List.of(
                segmentDetail("AL-240", "1000", "50.0"),
                segmentDetail("AL-240", "500", "70.5"),
                segmentDetail("AL-120", "200", "30.0"),
                segmentDetail(null, "75", null));

        var totals = ReportService.conductorTotals(segments);

        assertThat(totals.keySet()).containsExactly("AL-240", "AL-120", "Not reported");
        assertThat(totals.get("AL-240").segments()).isEqualTo(2);
        assertThat(totals.get("AL-240").lengthMeters()).isEqualByComparingTo("1500");
        // Peak, not average: the worst-loaded segment is what decides whether the choice holds.
        assertThat(totals.get("AL-240").peakUtilisationPct()).isEqualByComparingTo("70.5");
        // Unknown conductor is labelled, not dropped, so the lengths still add up to the network.
        assertThat(totals.get("Not reported").lengthMeters()).isEqualByComparingTo("75");
    }

    private static RouteSegmentDetail segmentDetail(String cableType, String length, String utilisation) {
        return new RouteSegmentDetail(
                "FDR-001", "S", new BigDecimal(length), 0, BigDecimal.ZERO, BigDecimal.ZERO,
                cableType, utilisation != null ? new BigDecimal(utilisation) : null,
                null, null, null, null, 0, null);
    }

    private record Fixture(Project project, OptimizationJob job) { }

    private Fixture fixture(UUID projectId, UUID jobId) {
        Project project = new Project("Test Project", "Description");
        org.springframework.test.util.ReflectionTestUtils.setField(project, "id", projectId);
        OptimizationJob job = new OptimizationJob(project, "MULTI_OBJECTIVE_A_STAR", null, null, null, null);
        org.springframework.test.util.ReflectionTestUtils.setField(job, "id", jobId);

        when(projectRepository.findById(projectId)).thenReturn(Optional.of(project));
        when(jobRepository.findById(jobId)).thenReturn(Optional.of(job));
        return new Fixture(project, job);
    }

    private GeneratedRoute segment(
            OptimizationJob job, String feeder, String segmentId, String length, String cost, String losses) {
        LineString path = geometryFactory.createLineString(new Coordinate[]{
                new Coordinate(77.23, 28.63),
                new Coordinate(77.25, 28.64)
        });
        GeneratedRoute route = new GeneratedRoute(job, feeder, new BigDecimal(length), null,
                new BigDecimal(losses), 0, path, null, segmentId);
        // The engine's own conductor price for this segment. The route's total_cost is deliberately
        // left null: it used to hold a length x 80 fabrication.
        route.applyConductorCost(cost != null ? new BigDecimal(cost) : null);
        return route;
    }
}
