package com.power.surge.service;

import com.power.surge.domain.CadastralParcel;
import com.power.surge.domain.GeneratedRoute;
import com.power.surge.domain.JobStatus;
import com.power.surge.domain.OptimizationJob;
import com.power.surge.domain.Project;
import com.power.surge.dto.report.EngineeringBomReportResponse;
import com.power.surge.repository.CadastralParcelRepository;
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
    private CadastralParcelRepository parcelRepository;

    private ReportService reportService;
    private final GeometryFactory geometryFactory = new GeometryFactory(new PrecisionModel(), Project.WGS84_SRID);

    @BeforeEach
    void setUp() {
        reportService = new ReportService(projectRepository, jobRepository, routeRepository, parcelRepository);
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
                job, "Feeder-01", new BigDecimal("2500.00"), new BigDecimal("150000.00"), new BigDecimal("12.5"), 15, lineString, null
        );

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
        when(parcelRepository.findAllByProjectIdOrderByParcelIdAsc(projectId)).thenReturn(List.of(parcel));

        EngineeringBomReportResponse report = reportService.generateBomReport(projectId, jobId);

        assertThat(report).isNotNull();
        assertThat(report.projectName()).isEqualTo("Test Project");
        assertThat(report.totalFeeders()).isEqualTo(1);
        assertThat(report.totalPoles()).isEqualTo(15);
        assertThat(report.feederSummaries()).hasSize(1);
        assertThat(report.parcelImpactSummaries()).hasSize(1);
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
                job, "Feeder-01", new BigDecimal("2500.00"), new BigDecimal("150000.00"), new BigDecimal("12.5"), 15, lineString, null
        );

        when(projectRepository.findById(projectId)).thenReturn(Optional.of(project));
        when(jobRepository.findById(jobId)).thenReturn(Optional.of(job));
        when(routeRepository.findAllByJobIdOrderByFeederNameAsc(jobId)).thenReturn(List.of(route));
        when(parcelRepository.findAllByProjectIdOrderByParcelIdAsc(projectId)).thenReturn(List.of());

        String csv = reportService.generateBomCsv(projectId, jobId);

        assertThat(csv).contains("SURGE Engineering Bill of Materials (BOM) Report");
        assertThat(csv).contains("Feeder-01");
        assertThat(csv).contains("2500.00");
    }

    @Test
    void getScenarioComparison_success() {
        UUID projectId = UUID.randomUUID();
        Project project = new Project("Test Project", "Description");

        when(projectRepository.findById(projectId)).thenReturn(Optional.of(project));
        when(jobRepository.findAllByProjectIdOrderByCreatedAtDesc(projectId)).thenReturn(List.of());

        com.power.surge.dto.report.ScenarioComparisonResponse resp = reportService.getScenarioComparison(projectId);

        assertThat(resp).isNotNull();
        assertThat(resp.scenarios()).hasSize(4);
    }
}
