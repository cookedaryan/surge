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
import com.power.surge.dto.report.ReportRunParameters;
import com.power.surge.dto.report.RouteSegmentDetail;
import org.locationtech.jts.geom.Coordinate;
import org.locationtech.jts.geom.LineString;
import org.locationtech.jts.geom.Point;
import com.power.surge.repository.CadastralParcelRepository;
import com.power.surge.repository.GeneratedPoleRepository;
import com.power.surge.repository.GeneratedRouteRepository;
import com.power.surge.repository.OptimizationJobRepository;
import com.power.surge.repository.ProjectRepository;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.math.BigDecimal;
import java.math.RoundingMode;
import java.time.Instant;
import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Objects;
import java.util.Map;
import java.util.UUID;

@Service
@Transactional(readOnly = true)
public class ReportService {

    private final ProjectRepository projectRepository;
    private final OptimizationJobRepository jobRepository;
    private final GeneratedRouteRepository routeRepository;
    private final GeneratedPoleRepository poleRepository;
    private static final Logger log = LoggerFactory.getLogger(ReportService.class);

    /**
     * Right-of-way corridor width used for land-impact figures, in metres.
     *
     * <p>Mirrors the {@code rowWidthM} default on the job request. The chosen value is not
     * persisted on the job today, so it is stated in the exported report rather than left as a
     * silent assumption behind a compensation number.
     */
    private static final double DEFAULT_ROW_WIDTH_M = 18.0;

    private final CadastralParcelRepository parcelRepository;
    private final AuditLogService auditLogService;
    private final CableCatalogueService cableCatalogueService;

    public ReportService(
            ProjectRepository projectRepository,
            OptimizationJobRepository jobRepository,
            GeneratedRouteRepository routeRepository,
            GeneratedPoleRepository poleRepository,
            CadastralParcelRepository parcelRepository,
            AuditLogService auditLogService,
            CableCatalogueService cableCatalogueService
    ) {
        this.projectRepository = projectRepository;
        this.jobRepository = jobRepository;
        this.routeRepository = routeRepository;
        this.poleRepository = poleRepository;
        this.parcelRepository = parcelRepository;
        this.auditLogService = auditLogService;
        this.cableCatalogueService = cableCatalogueService;
    }

    public EngineeringBomReportResponse generateBomReport(UUID projectId, UUID jobId) {
        Project project = getProjectOrThrow(projectId);
        OptimizationJob job = resolveJob(projectId, jobId);

        List<GeneratedRoute> routes = routeRepository.findAllByJobIdOrderByFeederNameAsc(job.getId());
        List<CadastralParcel> parcels = parcelRepository.findAllByProjectIdOrderByParcelIdAsc(projectId);

        List<GeneratedPole> poles = poleRepository.findAllByJobIdOrderByPoleIdentifierAsc(job.getId());
        Map<String, Long> poleCountBySegment = poleCountBySegmentId(poles);

        List<RouteSegmentDetail> segmentDetails = new ArrayList<>();
        BigDecimal totalLength = BigDecimal.ZERO;
        BigDecimal totalLosses = BigDecimal.ZERO;

        for (GeneratedRoute r : routes) {
            // GeneratedRoute.poleCount is only ever a /150m fallback estimate (routes are persisted
            // before real pole placement runs, and can predate it entirely for older jobs). Prefer
            // the real per-segment count so this matches what the map popup shows for this route.
            Long realCount = r.getSegmentId() != null ? poleCountBySegment.get(r.getSegmentId()) : null;
            int rowPoleCount = realCount != null ? realCount.intValue() : (r.getPoleCount() != null ? r.getPoleCount() : 0);

            segmentDetails.add(toSegmentDetail(r, rowPoleCount));

            if (r.getTotalLengthMeters() != null) {
                totalLength = totalLength.add(r.getTotalLengthMeters());
            }
            if (r.getElectricalLossesKw() != null) {
                totalLosses = totalLosses.add(r.getElectricalLossesKw());
            }
        }

        List<FeederBomSummary> feederSummaries = rollUpByFeeder(segmentDetails);

        // The network total counts each physical pole once, even where a junction pole is shared
        // by two segments and so appears in both of their row counts above.
        int totalPoles = !poles.isEmpty() ? poles.size() : feederSummaries.stream().mapToInt(FeederBomSummary::poleCount).sum();

        // Land compensation is owed for the ground the line actually occupies, so the area comes
        // from intersecting each parcel with the routes' right-of-way corridor, measured on the
        // ellipsoid by PostGIS. It previously used the parcel's entire area, converted with a
        // fixed metres-per-degree factor and then scaled by an unexplained 0.001 — which on the
        // reference project reported 38 m² against a true corridor overlap of 18,884 m².
        Map<String, Double> affectedAreaByParcel = rowCorridorAreaByParcel(projectId, job.getId());

        LandOutcome landOutcome = LandOutcome.fromResultSummaryJson(job.getResultSummaryJson());

        List<ParcelImpactSummary> parcelSummaries = new ArrayList<>();
        for (CadastralParcel p : parcels) {
            Double affectedArea = affectedAreaByParcel.getOrDefault(p.getParcelId(), 0.0);
            BigDecimal costRate = p.getAcquisitionCostPerM2() != null ? p.getAcquisitionCostPerM2() : BigDecimal.ZERO;
            BigDecimal estimatedComp = costRate.multiply(BigDecimal.valueOf(affectedArea)).setScale(2, RoundingMode.HALF_UP);

            String ownerId = null;
            String availabilityStatus = null;
            String transactionMode = null;
            BigDecimal selectedPresentValue = null;
            String priceBasis = null;
            String priceDate = null;
            if (landOutcome != null && landOutcome.parcelDecisions().containsKey(p.getParcelId())) {
                LandOutcome.LandParcelDecision d = landOutcome.parcelDecisions().get(p.getParcelId());
                ownerId = d.ownerId();
                availabilityStatus = d.availabilityStatus();
                transactionMode = d.selectedMode();
                selectedPresentValue = d.selectedPresentValue();
                priceBasis = d.costBasis();
                priceDate = d.priceDate();
            }

            parcelSummaries.add(new ParcelImpactSummary(
                    p.getParcelId(),
                    p.getOwnerName(),
                    ownerId,
                    p.getAcquisitionCostPerM2(),
                    affectedArea,
                    estimatedComp,
                    availabilityStatus,
                    transactionMode,
                    selectedPresentValue,
                    priceBasis,
                    priceDate
            ));
        }

        BigDecimal rowWidth = job.getRowWidthM() != null ? job.getRowWidthM() : BigDecimal.valueOf(DEFAULT_ROW_WIDTH_M);
        BigDecimal totalAffectedArea = parcelSummaries.stream()
                .map(p -> BigDecimal.valueOf(p.affectedAreaM2()))
                .reduce(BigDecimal.ZERO, BigDecimal::add)
                .setScale(2, RoundingMode.HALF_UP);
        BigDecimal totalCompensation = parcelSummaries.stream()
                .map(ParcelImpactSummary::estimatedCompensationCost)
                .filter(Objects::nonNull)
                .reduce(BigDecimal.ZERO, BigDecimal::add)
                .setScale(2, RoundingMode.HALF_UP);

        return new EngineeringBomReportResponse(
                projectId,
                project.getName(),
                job.getId(),
                toRunParameters(job),
                // Distinct feeders. This used to be routes.size(), which reported the reference
                // project as having 38 feeders when it has seven spanning 38 segments.
                feederSummaries.size(),
                segmentDetails.size(),
                totalLength.setScale(2, RoundingMode.HALF_UP),
                totalPoles,
                countBy(poles, GeneratedPole::getPoleRole),
                countBy(poles, GeneratedPole::getRecommendedPoleType),
                // The engine's own network CAPEX -- conductor, poles and land together -- rather
                // than a sum of per-route figures, which would omit poles and land and present the
                // remainder as a total.
                job.getTotalCapex(),
                job.getCostCurrency(),
                job.getCostFailureCount(),
                job.getConductorCapex(),
                job.getPoleCapex(),
                job.getLandCapex(),
                job.getAnnualLossEnergyMwh(),
                job.getAnnualLossCost(),
                job.getPresentValueOpex(),
                job.getLifecycleCost(),
                totalLosses.setScale(2, RoundingMode.HALF_UP),
                rowWidth,
                totalAffectedArea,
                totalCompensation,
                feederSummaries,
                segmentDetails,
                poles.stream().map(ReportService::toScheduleEntry).toList(),
                landOutcome != null ? landOutcome.ownerInteractionCount() : null,
                landOutcome != null ? landOutcome.ownerInteractionBasis() : null,
                landOutcome != null ? landOutcome.landCostBasis() : null,
                landOutcome != null ? landOutcome.isFeasible() : null,
                parcelSummaries,
                Instant.now()
        );
    }

    /**
     * Rolls the per-segment schedule up to one row per feeder.
     *
     * <p>Pole counts are summed from the segment rows, where a junction pole shared by two segments
     * is counted toward each. That is deliberate at segment level — a crew at either segment sees
     * that pole — but it means the feeder totals can exceed the network total, which counts each
     * physical pole once. The two figures answer different questions.
     */
    private static List<FeederBomSummary> rollUpByFeeder(List<RouteSegmentDetail> segments) {
        Map<String, List<RouteSegmentDetail>> byFeeder = new LinkedHashMap<>();
        for (RouteSegmentDetail s : segments) {
            byFeeder.computeIfAbsent(s.feederName() != null ? s.feederName() : "Unassigned", k -> new ArrayList<>())
                    .add(s);
        }

        List<FeederBomSummary> summaries = new ArrayList<>();
        for (Map.Entry<String, List<RouteSegmentDetail>> e : byFeeder.entrySet()) {
            List<RouteSegmentDetail> rows = e.getValue();
            summaries.add(new FeederBomSummary(
                    e.getKey(),
                    rows.size(),
                    sum(rows, RouteSegmentDetail::lengthMeters),
                    rows.stream().mapToInt(r -> r.poleCount() != null ? r.poleCount() : 0).sum(),
                    sumMoney(rows, RouteSegmentDetail::conductorCost),
                    sum(rows, RouteSegmentDetail::electricalLossesKw)
            ));
        }
        return summaries;
    }

    /**
     * Sums money, returning null when no row carried any.
     *
     * <p>{@link #sum} folds from zero, which is right for lengths and losses and wrong for money: a
     * feeder nobody priced would report 0, and a cost of zero reads as free rather than as unknown.
     */
    private static BigDecimal sumMoney(
            List<RouteSegmentDetail> rows,
            java.util.function.Function<RouteSegmentDetail, BigDecimal> field
    ) {
        List<BigDecimal> values = rows.stream().map(field).filter(Objects::nonNull).toList();
        if (values.isEmpty()) {
            return null;
        }
        return values.stream().reduce(BigDecimal.ZERO, BigDecimal::add).setScale(2, RoundingMode.HALF_UP);
    }

    private static BigDecimal sum(
            List<RouteSegmentDetail> rows,
            java.util.function.Function<RouteSegmentDetail, BigDecimal> field
    ) {
        return rows.stream()
                .map(field)
                .filter(Objects::nonNull)
                .reduce(BigDecimal.ZERO, BigDecimal::add)
                .setScale(3, RoundingMode.HALF_UP);
    }

    /** Counts poles by some attribute, skipping those where it was never recorded. */
    private static Map<String, Integer> countBy(
            List<GeneratedPole> poles,
            java.util.function.Function<GeneratedPole, String> attribute
    ) {
        Map<String, Integer> counts = new java.util.TreeMap<>();
        for (GeneratedPole p : poles) {
            String key = attribute.apply(p);
            if (key != null && !key.isBlank()) {
                counts.merge(key, 1, Integer::sum);
            }
        }
        return counts;
    }

    private static ReportRunParameters toRunParameters(OptimizationJob job) {
        return new ReportRunParameters(
                job.getScenario(),
                job.getAlgorithmType(),
                job.getStatus() != null ? job.getStatus().name() : null,
                job.getVoltageKv(),
                job.getFeederCapacityMw(),
                job.getMaxSpanMeters(),
                job.getMaxVoltageDropPct(),
                job.getRowWidthM(),
                job.getCapexWeight(),
                job.getLossesWeight(),
                job.getStartedAt(),
                job.getCompletedAt()
        );
    }

    private static RouteSegmentDetail toSegmentDetail(GeneratedRoute route, int poleCount) {
        LineString path = route.getRoutePath();
        Coordinate start = path != null && path.getNumPoints() > 0 ? path.getCoordinateN(0) : null;
        Coordinate end = path != null && path.getNumPoints() > 0
                ? path.getCoordinateN(path.getNumPoints() - 1)
                : null;

        return new RouteSegmentDetail(
                route.getFeederName(),
                route.getSegmentId(),
                route.getTotalLengthMeters(),
                poleCount,
                route.getConductorCost(),
                route.getElectricalLossesKw(),
                route.getCableTypeId(),
                route.getCableUtilisationPct(),
                start != null ? start.getY() : null,
                start != null ? start.getX() : null,
                end != null ? end.getY() : null,
                end != null ? end.getX() : null,
                path != null ? path.getNumPoints() : 0,
                path != null ? path.toText() : null
        );
    }

    private static PoleScheduleEntry toScheduleEntry(GeneratedPole pole) {
        Point location = pole.getLocation();
        List<String> segments = pole.getConnectedRouteIds();

        return new PoleScheduleEntry(
                pole.getPoleIdentifier(),
                pole.getFeederName(),
                pole.getPoleRole(),
                pole.getRecommendedPoleType(),
                location != null ? location.getY() : null,
                location != null ? location.getX() : null,
                segments != null ? String.join(" | ", segments) : null
        );
    }

    /**
     * Per-parcel right-of-way overlap, keyed by parcel id.
     *
     * <p>Returns an empty map if the spatial query cannot run, which makes every parcel report zero
     * affected area. That is the honest failure mode: better to show no impact than to invent a
     * figure that feeds a compensation estimate.
     */
    private Map<String, Double> rowCorridorAreaByParcel(UUID projectId, UUID jobId) {
        try {
            Map<String, Double> areas = new LinkedHashMap<>();
            for (Object[] row : parcelRepository.findRowCorridorAreaByParcel(
                    projectId, jobId, DEFAULT_ROW_WIDTH_M / 2.0)) {
                if (row.length >= 2 && row[0] != null && row[1] != null) {
                    areas.put(String.valueOf(row[0]), ((Number) row[1]).doubleValue());
                }
            }
            return areas;
        } catch (RuntimeException e) {
            log.warn("Could not compute right-of-way parcel overlap for job {}: {}", jobId, e.toString());
            return Map.of();
        }
    }

    public String generateBomCsv(UUID projectId, UUID jobId) {
        EngineeringBomReportResponse report = generateBomReport(projectId, jobId);

        // Audited here rather than in generateBomReport: that method also backs the always-visible
        // BOM panel, so auditing it would bury real actions under a stream of page renders. Taking
        // data out of the system is the event worth recording.
        auditLogService.record("REPORT_EXPORTED", "PROJECT", projectId.toString(),
                "Exported BOM CSV for project '" + report.projectName() + "'"
                        + (report.jobId() != null ? " (job " + report.jobId() + ")" : ""));

        StringBuilder csv = new StringBuilder();
        ReportRunParameters run = report.runParameters();

        csv.append("SURGE Engineering Bill of Materials\n");
        csv.append("Project Name,").append(escapeCsv(report.projectName())).append("\n");
        csv.append("Project ID,").append(report.projectId()).append("\n");
        csv.append("Job ID,").append(report.jobId()).append("\n");
        csv.append("Generated At,").append(report.generatedAt()).append("\n\n");

        // Without the inputs the figures below cannot be reproduced or checked: the same site
        // yields a different network at a different voltage, capacity or span limit.
        csv.append("--- RUN PARAMETERS ---\n");
        csv.append("Scenario,").append(escapeCsv(run.scenario())).append("\n");
        csv.append("Algorithm,").append(escapeCsv(run.algorithmType())).append("\n");
        csv.append("Status,").append(escapeCsv(run.status())).append("\n");
        csv.append("Voltage (kV),").append(nullToBlank(run.voltageKv())).append("\n");
        csv.append("Feeder capacity (MW),").append(nullToBlank(run.feederCapacityMw())).append("\n");
        csv.append("Max span (m),").append(nullToBlank(run.maxSpanMeters())).append("\n");
        csv.append("Max voltage drop (%),").append(nullToBlank(run.maxVoltageDropPct())).append("\n");
        csv.append("ROW width (m),").append(nullToBlank(report.rowWidthMeters())).append("\n");
        csv.append("Capex weight,").append(nullToBlank(run.capexWeight())).append("\n");
        csv.append("Losses weight,").append(nullToBlank(run.lossesWeight())).append("\n");
        csv.append("Started at,").append(nullToBlank(run.startedAt())).append("\n");
        csv.append("Completed at,").append(nullToBlank(run.completedAt())).append("\n\n");

        csv.append("--- NETWORK TOTALS ---\n");
        csv.append("Feeders,").append(report.totalFeeders()).append("\n");
        csv.append("Segments,").append(report.totalSegments()).append("\n");
        csv.append("Network length (m),").append(report.totalNetworkLengthMeters()).append("\n");
        csv.append("Network length (km),")
                .append(report.totalNetworkLengthMeters().divide(BigDecimal.valueOf(1000), 3, RoundingMode.HALF_UP))
                .append("\n");
        csv.append("Poles (distinct),").append(report.totalPoles()).append("\n");
        csv.append("Estimated capex").append(currencyLabel(report.costCurrency())).append(",")
                .append(money(report.totalEstimatedCost())).append("\n");
        if (report.costFailureCount() != null && report.costFailureCount() > 0) {
            // The engine omits a component it could not price rather than pricing it at zero, so the
            // capex above is a partial sum. Saying so is the difference between a figure and a
            // misleading one.
            csv.append("Cost components not priced,").append(report.costFailureCount())
                    .append(" (capex above is incomplete)\n");
        }
        csv.append("Electrical losses (kW),").append(report.totalElectricalLossesKw()).append("\n");
        csv.append("Affected area (m2),").append(report.totalAffectedAreaM2()).append("\n");
        csv.append("Estimated compensation,").append(nullToZero(report.totalCompensationCost())).append("\n\n");

        csv.append("--- POLE COUNT BY STRUCTURAL ROLE ---\n");
        csv.append("Role,Count\n");
        for (Map.Entry<String, Integer> e : report.poleCountByRole().entrySet()) {
            csv.append(escapeCsv(e.getKey())).append(",").append(e.getValue()).append("\n");
        }
        csv.append("\n");

        csv.append("--- POLE COUNT BY RECOMMENDED TYPE ---\n");
        csv.append("Recommended Type,Count\n");
        for (Map.Entry<String, Integer> e : report.poleCountByType().entrySet()) {
            csv.append(escapeCsv(e.getKey())).append(",").append(e.getValue()).append("\n");
        }
        csv.append("\n");

        csv.append("--- FEEDER SUMMARY ---\n");
        // "Conductor Cost", not "Total Cost": conductor is the only component the engine attributes
        // to a route, and calling a partial figure a total is how a reader is misled.
        csv.append("Feeder Name,Segments,Length (m),Pole Count,Conductor Cost")
                .append(currencyLabel(report.costCurrency()))
                .append(",Electrical Losses (kW)\n");
        for (FeederBomSummary f : report.feederSummaries()) {
            csv.append(escapeCsv(f.feederName())).append(",")
                    .append(f.segmentCount()).append(",")
                    .append(nullToZero(f.lengthMeters())).append(",")
                    .append(f.poleCount()).append(",")
                    .append(money(f.conductorCost())).append(",")
                    .append(nullToZero(f.electricalLossesKw())).append("\n");
        }
        // Feeder pole counts sum higher than the distinct network total: a junction pole shared by
        // two segments is counted toward each, because a crew at either segment has to set it.
        csv.append("TOTALS,")
                .append(report.totalSegments()).append(",")
                .append(report.totalNetworkLengthMeters()).append(",")
                .append(report.totalPoles()).append(",")
                // money(...), not the BigDecimal: appending null renders the literal "null".
                .append(money(report.totalEstimatedCost())).append(",")
                .append(report.totalElectricalLossesKw()).append("\n\n");

        // Conductor length by type is what a procurement team orders against, so it is totalled
        // here rather than left to be summed out of the segment schedule by hand.
        csv.append("--- CONDUCTOR SCHEDULE ---\n");
        // Stated before the numbers rather than after them: unverified conductor parameters
        // produce losses, voltage drops and utilisations that look exactly as authoritative as
        // verified ones, and a reader who has already accepted the table will not revisit it.
        csv.append("Catalogue basis,").append(escapeCsv(
                cableCatalogueService.describeProvenance(
                        run.voltageKv() != null ? run.voltageKv() : new BigDecimal("33.00")))).append("\n");
        csv.append("Cable Type,Segments,Length (m),Peak Utilisation (%)\n");
        for (Map.Entry<String, ConductorTotals> e : conductorTotals(report.segmentDetails()).entrySet()) {
            csv.append(escapeCsv(e.getKey())).append(",")
                    .append(e.getValue().segments()).append(",")
                    .append(e.getValue().lengthMeters().toPlainString()).append(",")
                    .append(e.getValue().peakUtilisationPct() != null
                            ? e.getValue().peakUtilisationPct().toPlainString() : "")
                    .append("\n");
        }
        csv.append("\n");

        csv.append("--- ROUTE SEGMENT SCHEDULE ---\n");
        csv.append("Feeder Name,Segment ID,Length (m),Pole Count,Conductor Cost,Electrical Losses (kW),"
                + "Cable Type,Cable Utilisation (%),"
                + "Start Latitude,Start Longitude,End Latitude,End Longitude,Vertices,Path (WKT)\n");
        for (RouteSegmentDetail s : report.segmentDetails()) {
            csv.append(escapeCsv(s.feederName())).append(",")
                    .append(escapeCsv(s.segmentId())).append(",")
                    .append(nullToZero(s.lengthMeters())).append(",")
                    .append(s.poleCount() != null ? s.poleCount() : 0).append(",")
                    .append(money(s.conductorCost())).append(",")
                    .append(nullToZero(s.electricalLossesKw())).append(",")
                    .append(escapeCsv(s.cableTypeId())).append(",")
                    .append(s.cableUtilisationPct() != null
                            ? s.cableUtilisationPct().toPlainString() : "").append(",")
                    .append(coord(s.startLatitude())).append(",")
                    .append(coord(s.startLongitude())).append(",")
                    .append(coord(s.endLatitude())).append(",")
                    .append(coord(s.endLongitude())).append(",")
                    .append(s.vertexCount() != null ? s.vertexCount() : 0).append(",")
                    .append(escapeCsv(s.pathWkt())).append("\n");
        }
        csv.append("\n");

        csv.append("--- POLE SETTING-OUT SCHEDULE ---\n");
        csv.append("Coordinate system,WGS 84 (EPSG:4326) decimal degrees\n");
        csv.append("Pole ID,Feeder Name,Structural Role,Recommended Type,Latitude,Longitude,Connected Segments\n");
        for (PoleScheduleEntry p : report.poleSchedule()) {
            csv.append(escapeCsv(p.poleIdentifier())).append(",")
                    .append(escapeCsv(p.feederName())).append(",")
                    .append(escapeCsv(p.role())).append(",")
                    .append(escapeCsv(p.recommendedPoleType())).append(",")
                    .append(coord(p.latitude())).append(",")
                    .append(coord(p.longitude())).append(",")
                    .append(escapeCsv(p.connectedSegments())).append("\n");
        }
        csv.append("\n");

        csv.append("--- CADASTRAL PARCEL IMPACT & COMPENSATION ---\n");
        csv.append("ROW corridor width (m),").append(nullToBlank(report.rowWidthMeters())).append("\n");
        csv.append("Affected area basis,Route right-of-way corridor intersected with parcel (ellipsoidal)\n");
        csv.append("Parcel ID,Owner Name,Rate ($/m2),Affected Area (m2),Estimated Compensation ($)\n");

        for (ParcelImpactSummary p : report.parcelImpactSummaries()) {
            csv.append(escapeCsv(p.parcelId())).append(",")
                    .append(escapeCsv(p.ownerName() != null ? p.ownerName() : "")).append(",")
                    .append(p.acquisitionCostPerM2() != null ? p.acquisitionCostPerM2() : 0.0).append(",")
                    .append(String.format("%.2f", p.affectedAreaM2())).append(",")
                    .append(p.estimatedCompensationCost()).append("\n");
        }
        csv.append("TOTALS,,,")
                .append(report.totalAffectedAreaM2()).append(",")
                .append(report.totalCompensationCost()).append("\n");

        return csv.toString();
    }

    /** Conductor length and peak loading for one cable type across the network. */
    record ConductorTotals(int segments, BigDecimal lengthMeters, BigDecimal peakUtilisationPct) {
    }

    /**
     * Totals conductor by type, ordered longest first.
     *
     * <p>Segments whose conductor is unknown are grouped under an explicit label rather than
     * dropped, so the reported lengths still add up to the network and a gap in the data is
     * visible instead of silently absorbed.
     */
    static Map<String, ConductorTotals> conductorTotals(List<RouteSegmentDetail> segments) {
        Map<String, ConductorTotals> totals = new LinkedHashMap<>();
        for (RouteSegmentDetail s : segments) {
            String type = s.cableTypeId() != null ? s.cableTypeId() : "Not reported";
            ConductorTotals existing = totals.get(type);
            BigDecimal length = s.lengthMeters() != null ? s.lengthMeters() : BigDecimal.ZERO;
            BigDecimal peak = s.cableUtilisationPct();

            if (existing == null) {
                totals.put(type, new ConductorTotals(1, length, peak));
            } else {
                BigDecimal newPeak = existing.peakUtilisationPct();
                if (peak != null && (newPeak == null || peak.compareTo(newPeak) > 0)) {
                    newPeak = peak;
                }
                totals.put(type, new ConductorTotals(
                        existing.segments() + 1,
                        existing.lengthMeters().add(length),
                        newPeak));
            }
        }
        return totals.entrySet().stream()
                .sorted((a, b) -> b.getValue().lengthMeters().compareTo(a.getValue().lengthMeters()))
                .collect(java.util.stream.Collectors.toMap(
                        Map.Entry::getKey, Map.Entry::getValue, (a, b) -> a, LinkedHashMap::new));
    }

    /** Six decimals is ~0.11 m — finer than a pole can be positioned, and never scientific notation. */
    private static String coord(Double value) {
        return value != null ? String.format("%.6f", value) : "";
    }

    private static String nullToBlank(Object value) {
        return value != null ? value.toString() : "";
    }

    private static String nullToZero(BigDecimal value) {
        return value != null ? value.toPlainString() : "0";
    }

    /**
     * Money for a report cell: the figure, or "Not costed".
     *
     * <p>Never zero. An unpriced network and a free one are different findings and only one of them
     * is possible, so a 0 in a capex column misleads a reader without anyone having lied.
     */
    private static String money(BigDecimal value) {
        return value != null ? value.toPlainString() : "Not costed";
    }

    /** The currency of a run's figures, for a column heading. Blank when nothing was costed. */
    private static String currencyLabel(String currency) {
        return currency != null && !currency.isBlank() ? " (" + currency + ")" : "";
    }

    private static final List<String> SCENARIO_NAMES =
            List.of("Balanced", "Minimum Cost", "Minimum Land Impact", "Minimum Environmental Impact");

    /**
     * Compares actual completed jobs per scenario for this project. A scenario the user hasn't
     * run yet is simply omitted rather than filled in with an invented number — the previous
     * implementation returned the same four hardcoded length/pole/cost figures for every project
     * regardless of what was actually run.
     */
    public com.power.surge.dto.report.ScenarioComparisonResponse getScenarioComparison(UUID projectId) {
        getProjectOrThrow(projectId);
        List<OptimizationJob> jobs = jobRepository.findAllByProjectIdOrderByCreatedAtDesc(projectId);

        // Prefer the most recent completed Balanced run as the delta baseline; fall back to
        // whatever scenario was run most recently if Balanced hasn't been, so deltas still have
        // a reference point instead of silently disappearing.
        OptimizationJob baseJob = jobs.stream()
                .filter(j -> j.getStatus() == JobStatus.COMPLETED && "Balanced".equalsIgnoreCase(j.getScenario()))
                .findFirst()
                .orElseGet(() -> jobs.stream().filter(j -> j.getStatus() == JobStatus.COMPLETED).findFirst().orElse(null));

        Double baseCost = null;
        Double baseLosses = null;
        if (baseJob != null) {
            EngineeringBomReportResponse baseReport = generateBomReport(projectId, baseJob.getId());
            baseCost = baseReport.totalEstimatedCost() != null ? baseReport.totalEstimatedCost().doubleValue() : null;
            baseLosses = baseReport.totalElectricalLossesKw() != null ? baseReport.totalElectricalLossesKw().doubleValue() : null;
        }

        List<com.power.surge.dto.report.ScenarioSummaryItem> items = new ArrayList<>();
        for (String scName : SCENARIO_NAMES) {
            OptimizationJob scJob = jobs.stream()
                    .filter(j -> j.getStatus() == JobStatus.COMPLETED && scName.equalsIgnoreCase(j.getScenario()))
                    .findFirst()
                    .orElse(null);
            if (scJob == null) {
                continue;
            }

            EngineeringBomReportResponse report = generateBomReport(projectId, scJob.getId());
            Double length = report.totalNetworkLengthMeters() != null ? report.totalNetworkLengthMeters().doubleValue() : null;
            Double cost = report.totalEstimatedCost() != null ? report.totalEstimatedCost().doubleValue() : null;
            Double losses = report.totalElectricalLossesKw() != null ? report.totalElectricalLossesKw().doubleValue() : null;
            double landCost = report.parcelImpactSummaries().stream()
                    .map(ParcelImpactSummary::estimatedCompensationCost)
                    .filter(Objects::nonNull)
                    .mapToDouble(BigDecimal::doubleValue)
                    .sum();

            items.add(new com.power.surge.dto.report.ScenarioSummaryItem(
                    scName,
                    scJob.getId(),
                    scJob.getStatus(),
                    length,
                    report.totalPoles(),
                    cost,
                    losses,
                    landCost,
                    percentDelta(cost, baseCost),
                    percentDelta(losses, baseLosses)
            ));
        }

        return new com.power.surge.dto.report.ScenarioComparisonResponse(projectId, items);
    }

    private static Double percentDelta(Double value, Double base) {
        if (value == null || base == null || base == 0) {
            return null;
        }
        return Math.round(((value - base) / base) * 1000.0) / 10.0;
    }

    /**
     * Counts real placed poles per segment_id. A junction pole can carry more than one
     * segment_id (it's shared between the two edges that meet there), so it's counted once
     * toward each — matching what a rider would actually see standing at each individual segment.
     */
    private static Map<String, Long> poleCountBySegmentId(List<GeneratedPole> poles) {
        Map<String, Long> counts = new LinkedHashMap<>();
        for (GeneratedPole pole : poles) {
            List<String> routeIds = pole.getConnectedRouteIds();
            if (routeIds == null) {
                continue;
            }
            for (String routeId : routeIds) {
                counts.merge(routeId, 1L, Long::sum);
            }
        }
        return counts;
    }

    private Project getProjectOrThrow(UUID projectId) {
        return projectRepository.findById(projectId)
                .orElseThrow(() -> new ProjectNotFoundException(projectId));
    }

    private OptimizationJob resolveJob(UUID projectId, UUID jobId) {
        if (jobId != null) {
            OptimizationJob job = jobRepository.findById(jobId)
                    .orElseThrow(() -> new IllegalArgumentException("Optimization job not found: " + jobId));
            if (job.getProject().getId() != null && !job.getProject().getId().equals(projectId)) {
                throw new IllegalArgumentException("Job " + jobId + " does not belong to project " + projectId);
            }
            return job;
        }

        List<OptimizationJob> jobs = jobRepository.findAllByProjectIdOrderByCreatedAtDesc(projectId);
        return jobs.stream()
                .filter(j -> j.getStatus() == JobStatus.COMPLETED)
                .findFirst()
                .orElseGet(() -> jobs.stream().findFirst()
                        .orElseThrow(() -> new IllegalArgumentException("No optimization jobs found for project: " + projectId)));
    }

    private static String escapeCsv(String value) {
        if (value == null) {
            return "";
        }
        if (value.contains(",") || value.contains("\"") || value.contains("\n")) {
            return "\"" + value.replace("\"", "\"\"") + "\"";
        }
        return value;
    }
}
