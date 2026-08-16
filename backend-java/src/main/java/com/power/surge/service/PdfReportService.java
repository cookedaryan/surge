package com.power.surge.service;

import com.lowagie.text.Document;
import com.lowagie.text.Element;
import com.lowagie.text.Font;
import com.lowagie.text.FontFactory;
import com.lowagie.text.PageSize;
import com.lowagie.text.Paragraph;
import com.lowagie.text.Phrase;
import com.lowagie.text.pdf.PdfPCell;
import com.lowagie.text.pdf.PdfPTable;
import com.lowagie.text.pdf.PdfWriter;
import com.power.surge.dto.project.ProjectResponse;
import com.power.surge.dto.report.EngineeringBomReportResponse;
import com.power.surge.dto.report.FeederBomSummary;
import com.power.surge.dto.report.ParcelImpactSummary;
import com.power.surge.dto.report.PoleScheduleEntry;
import com.power.surge.dto.report.ReportRunParameters;
import com.power.surge.dto.report.RouteSegmentDetail;
import com.power.surge.dto.report.ScenarioComparisonResponse;
import com.power.surge.dto.report.ScenarioSummaryItem;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.awt.Color;
import java.io.ByteArrayOutputStream;
import java.math.BigDecimal;
import java.math.RoundingMode;
import java.time.Instant;
import java.time.ZoneId;
import java.time.format.DateTimeFormatter;
import java.util.Map;
import java.util.UUID;

/**
 * Renders the engineering bill of materials as a PDF.
 *
 * <p>Laid out landscape because the segment and pole schedules carry coordinates, and columns that
 * wrap are unusable for setting out. Long tables repeat their header row on every page.
 */
@Service
@Transactional(readOnly = true)
public class PdfReportService {

    private static final Logger log = LoggerFactory.getLogger(PdfReportService.class);

    private static final Color INK = new Color(15, 23, 42);
    private static final Color ACCENT = new Color(59, 130, 246);
    private static final Color BAND = new Color(241, 245, 249);

    private final ProjectService projectService;
    private final ReportService reportService;
    private final AuditLogService auditLogService;

    public PdfReportService(
            ProjectService projectService,
            ReportService reportService,
            AuditLogService auditLogService
    ) {
        this.projectService = projectService;
        this.reportService = reportService;
        this.auditLogService = auditLogService;
    }

    /**
     * @param jobId the run to report on, or null for the project's most recent completed run.
     *              This used to be hardcoded to null, so exporting while viewing an older run
     *              silently produced a report for a different one.
     */
    public byte[] generateExecutivePdfReport(UUID projectId, UUID jobId) {
        ProjectResponse project = projectService.getProject(projectId);
        EngineeringBomReportResponse bom = reportService.generateBomReport(projectId, jobId);

        auditLogService.record("REPORT_EXPORTED", "PROJECT", projectId.toString(),
                "Exported engineering PDF report for project '" + project.name() + "'"
                        + (bom.jobId() != null ? " (job " + bom.jobId() + ")" : ""));

        ScenarioComparisonResponse scenarios = null;
        try {
            scenarios = reportService.getScenarioComparison(projectId);
        } catch (RuntimeException e) {
            // A missing comparison must not cost the operator the whole bill of materials.
            log.warn("Scenario comparison unavailable for project {}: {}", projectId, e.getMessage());
        }

        ByteArrayOutputStream out = new ByteArrayOutputStream();
        Document document = new Document(PageSize.A4.rotate(), 28, 28, 28, 32);

        try {
            PdfWriter.getInstance(document, out);
            document.open();

            Font titleFont = FontFactory.getFont(FontFactory.HELVETICA_BOLD, 17, INK);
            Font subTitleFont = FontFactory.getFont(FontFactory.HELVETICA, 10, ACCENT);
            Font sectionFont = FontFactory.getFont(FontFactory.HELVETICA_BOLD, 12, INK);
            Font boldFont = FontFactory.getFont(FontFactory.HELVETICA_BOLD, 9, Color.BLACK);
            Font bodyFont = FontFactory.getFont(FontFactory.HELVETICA, 9, Color.DARK_GRAY);
            Font tinyFont = FontFactory.getFont(FontFactory.HELVETICA, 7, Color.DARK_GRAY);
            Font noteFont = FontFactory.getFont(FontFactory.HELVETICA_OBLIQUE, 8, Color.GRAY);
            Font footerFont = FontFactory.getFont(FontFactory.HELVETICA, 8, Color.GRAY);

            Paragraph title = new Paragraph("SURGE ENGINEERING BILL OF MATERIALS", titleFont);
            title.setAlignment(Element.ALIGN_CENTER);
            document.add(title);

            Paragraph sub = new Paragraph("Collector network and evacuation plan", subTitleFont);
            sub.setAlignment(Element.ALIGN_CENTER);
            sub.setSpacingAfter(14);
            document.add(sub);

            PdfPTable meta = new PdfPTable(4);
            meta.setWidthPercentage(100);
            meta.setSpacingAfter(14);
            addLabelled(meta, "Project", project.name(), boldFont, bodyFont);
            addLabelled(meta, "Project ID", project.id().toString(), boldFont, bodyFont);
            addLabelled(meta, "Optimisation job", bom.jobId() != null ? bom.jobId().toString() : "—", boldFont, bodyFont);
            addLabelled(meta, "Coordinate system", project.crs(), boldFont, bodyFont);
            addLabelled(meta, "Generated",
                    DateTimeFormatter.ISO_OFFSET_DATE_TIME.format(Instant.now().atZone(ZoneId.of("UTC"))),
                    boldFont, bodyFont);
            addLabelled(meta, "", "", boldFont, bodyFont);
            document.add(meta);

            section(document, "1. Run parameters", sectionFont);
            document.add(note("The network below is a product of these inputs. The same site yields a different "
                    + "network at a different voltage, feeder capacity or span limit.", noteFont));
            document.add(runParametersTable(bom, bodyFont, boldFont));

            section(document, "2. Network totals", sectionFont);
            document.add(totalsTable(bom, bodyFont));

            section(document, "3. Pole counts", sectionFont);
            // Two separate tables rather than one four-column table. Side by side, the independent
            // role and type lists lined up as though each row were a mapping — "intermediate"
            // appearing next to "shared junction pole" reads as a correspondence that is not there.
            document.add(countTable(bom.poleCountByRole(), "Structural role", bodyFont));
            document.add(countTable(bom.poleCountByType(), "Recommended type", bodyFont));

            section(document, "4. Feeder summary", sectionFont);
            document.add(feederTable(bom, bodyFont, boldFont));
            document.add(note("Feeder pole counts sum higher than the distinct network total: a junction pole "
                    + "shared by two segments is counted toward each, because it has to be set for either.",
                    noteFont));

            section(document, "5. Route segment schedule", sectionFont);
            document.add(note("Endpoints in WGS 84 decimal degrees. Full segment geometry is included in the "
                    + "CSV export as WKT.", noteFont));
            document.add(segmentTable(bom, tinyFont));

            section(document, "6. Pole setting-out schedule", sectionFont);
            document.add(note("WGS 84 (EPSG:4326) decimal degrees to six places — approximately 0.11 m.", noteFont));
            document.add(poleTable(bom, tinyFont));

            section(document, "7. Cadastral parcel impact and compensation", sectionFont);
            document.add(note("Affected area is the route right-of-way corridor intersected with each parcel, "
                    + "measured on the ellipsoid — not the parcel's full area.", noteFont));
            document.add(parcelTable(bom, bodyFont));

            if (scenarios != null && scenarios.scenarios() != null && !scenarios.scenarios().isEmpty()) {
                section(document, "8. Scenario comparison", sectionFont);
                document.add(scenarioTable(scenarios, bodyFont, boldFont));
            }

            Paragraph footer = new Paragraph(
                    "Generated by SURGE — confidential engineering evacuation plan", footerFont);
            footer.setAlignment(Element.ALIGN_CENTER);
            footer.setSpacingBefore(16);
            document.add(footer);

            document.close();
        } catch (Exception e) {
            throw new IllegalStateException("Failed to generate PDF report: " + e.getMessage(), e);
        }

        return out.toByteArray();
    }

    // --- sections ---------------------------------------------------------

    private PdfPTable runParametersTable(EngineeringBomReportResponse bom, Font body, Font bold) {
        ReportRunParameters run = bom.runParameters();
        PdfPTable t = new PdfPTable(4);
        t.setWidthPercentage(100);
        t.setSpacingAfter(12);

        addLabelled(t, "Scenario", text(run.scenario()), bold, body);
        addLabelled(t, "Algorithm", text(run.algorithmType()), bold, body);
        addLabelled(t, "Status", text(run.status()), bold, body);
        addLabelled(t, "Voltage", unit(run.voltageKv(), "kV"), bold, body);
        addLabelled(t, "Feeder capacity", unit(run.feederCapacityMw(), "MW"), bold, body);
        addLabelled(t, "Max span", unit(run.maxSpanMeters(), "m"), bold, body);
        addLabelled(t, "Max voltage drop", unit(run.maxVoltageDropPct(), "%"), bold, body);
        addLabelled(t, "ROW width", unit(bom.rowWidthMeters(), "m"), bold, body);
        addLabelled(t, "Capex weight", text(run.capexWeight()), bold, body);
        addLabelled(t, "Losses weight", text(run.lossesWeight()), bold, body);
        addLabelled(t, "Started", text(run.startedAt()), bold, body);
        addLabelled(t, "Completed", text(run.completedAt()), bold, body);
        return t;
    }

    private PdfPTable totalsTable(EngineeringBomReportResponse bom, Font body) {
        PdfPTable t = new PdfPTable(7);
        t.setWidthPercentage(100);
        t.setSpacingAfter(12);

        header(t, "Feeders", "Segments", "Network length", "Poles", "Estimated capex",
                "Electrical losses", "Compensation");

        BigDecimal km = bom.totalNetworkLengthMeters() != null
                ? bom.totalNetworkLengthMeters().divide(BigDecimal.valueOf(1000), 2, RoundingMode.HALF_UP)
                : BigDecimal.ZERO;

        cell(t, text(bom.totalFeeders()), body);
        cell(t, text(bom.totalSegments()), body);
        cell(t, km + " km", body);
        cell(t, text(bom.totalPoles()), body);
        cell(t, money(bom.totalEstimatedCost()), body);
        cell(t, unit(bom.totalElectricalLossesKw(), "kW"), body);
        cell(t, money(bom.totalCompensationCost()), body);
        return t;
    }

    private PdfPTable countTable(Map<String, Integer> counts, String label, Font body) {
        PdfPTable t = new PdfPTable(2);
        t.setWidthPercentage(55);
        t.setHorizontalAlignment(Element.ALIGN_LEFT);
        t.setSpacingAfter(10);
        header(t, label, "Count");

        if (counts.isEmpty()) {
            spanningNote(t, 2, "No poles recorded for this run.", body);
            return t;
        }
        int total = 0;
        for (Map.Entry<String, Integer> e : counts.entrySet()) {
            cell(t, e.getKey(), body);
            cell(t, String.valueOf(e.getValue()), body);
            total += e.getValue();
        }
        cell(t, "Total", body);
        cell(t, String.valueOf(total), body);
        return t;
    }

    private PdfPTable feederTable(EngineeringBomReportResponse bom, Font body, Font bold) throws Exception {
        PdfPTable t = new PdfPTable(6);
        t.setWidthPercentage(100);
        t.setWidths(new float[]{2.0f, 1.2f, 1.6f, 1.2f, 1.8f, 1.8f});
        t.setSpacingAfter(6);
        t.setHeaderRows(1);
        header(t, "Feeder", "Segments", "Length (km)", "Poles", "Est. cost", "Losses (kW)");

        if (bom.feederSummaries().isEmpty()) {
            spanningNote(t, 6, "No feeder routes generated for this run.", body);
            return t;
        }
        for (FeederBomSummary f : bom.feederSummaries()) {
            cell(t, f.feederName(), body);
            cell(t, text(f.segmentCount()), body);
            cell(t, km(f.lengthMeters()), body);
            cell(t, text(f.poleCount()), body);
            cell(t, money(f.totalCost()), body);
            cell(t, text(f.electricalLossesKw()), body);
        }
        return t;
    }

    private PdfPTable segmentTable(EngineeringBomReportResponse bom, Font tiny) throws Exception {
        PdfPTable t = new PdfPTable(10);
        t.setWidthPercentage(100);
        t.setWidths(new float[]{1.5f, 2.0f, 1.3f, 0.9f, 1.5f, 1.3f, 1.5f, 1.5f, 1.5f, 1.5f});
        t.setSpacingAfter(12);
        t.setHeaderRows(1);
        header(t, "Feeder", "Segment ID", "Length (m)", "Poles", "Est. cost", "Losses (kW)",
                "Start lat", "Start lon", "End lat", "End lon");

        if (bom.segmentDetails().isEmpty()) {
            spanningNote(t, 10, "No route segments generated for this run.", tiny);
            return t;
        }
        for (RouteSegmentDetail s : bom.segmentDetails()) {
            cell(t, s.feederName(), tiny);
            cell(t, s.segmentId(), tiny);
            cell(t, text(s.lengthMeters()), tiny);
            cell(t, text(s.poleCount()), tiny);
            cell(t, money(s.totalCost()), tiny);
            cell(t, text(s.electricalLossesKw()), tiny);
            cell(t, coord(s.startLatitude()), tiny);
            cell(t, coord(s.startLongitude()), tiny);
            cell(t, coord(s.endLatitude()), tiny);
            cell(t, coord(s.endLongitude()), tiny);
        }
        return t;
    }

    private PdfPTable poleTable(EngineeringBomReportResponse bom, Font tiny) throws Exception {
        PdfPTable t = new PdfPTable(6);
        t.setWidthPercentage(100);
        t.setWidths(new float[]{1.8f, 1.3f, 1.2f, 2.4f, 1.5f, 1.5f});
        t.setSpacingAfter(12);
        t.setHeaderRows(1);
        header(t, "Pole ID", "Feeder", "Role", "Recommended type", "Latitude", "Longitude");

        if (bom.poleSchedule().isEmpty()) {
            spanningNote(t, 6, "No poles placed for this run.", tiny);
            return t;
        }
        for (PoleScheduleEntry p : bom.poleSchedule()) {
            cell(t, p.poleIdentifier(), tiny);
            cell(t, p.feederName(), tiny);
            cell(t, p.role(), tiny);
            cell(t, p.recommendedPoleType(), tiny);
            cell(t, coord(p.latitude()), tiny);
            cell(t, coord(p.longitude()), tiny);
        }
        return t;
    }

    private PdfPTable parcelTable(EngineeringBomReportResponse bom, Font body) throws Exception {
        PdfPTable t = new PdfPTable(5);
        t.setWidthPercentage(100);
        t.setWidths(new float[]{1.6f, 2.4f, 1.4f, 1.8f, 1.8f});
        t.setSpacingAfter(12);
        t.setHeaderRows(1);
        header(t, "Parcel ID", "Owner", "Rate ($/m2)", "Affected area (m2)", "Compensation");

        if (bom.parcelImpactSummaries().isEmpty()) {
            spanningNote(t, 5, "No cadastral parcels recorded for this project.", body);
            return t;
        }
        for (ParcelImpactSummary p : bom.parcelImpactSummaries()) {
            cell(t, p.parcelId(), body);
            cell(t, p.ownerName() != null ? p.ownerName() : "", body);
            cell(t, text(p.acquisitionCostPerM2()), body);
            cell(t, String.format("%.2f", p.affectedAreaM2()), body);
            cell(t, money(p.estimatedCompensationCost()), body);
        }
        cell(t, "TOTAL", body);
        cell(t, "", body);
        cell(t, "", body);
        cell(t, text(bom.totalAffectedAreaM2()), body);
        cell(t, money(bom.totalCompensationCost()), body);
        return t;
    }

    private PdfPTable scenarioTable(ScenarioComparisonResponse scenarios, Font body, Font bold) throws Exception {
        PdfPTable t = new PdfPTable(5);
        t.setWidthPercentage(100);
        t.setWidths(new float[]{2.2f, 1.8f, 1.2f, 1.8f, 1.8f});
        t.setSpacingAfter(12);
        t.setHeaderRows(1);
        header(t, "Scenario", "Capex", "Poles", "Losses (kW)", "ROW cost");

        for (ScenarioSummaryItem item : scenarios.scenarios()) {
            cell(t, item.scenarioName(), bold);
            cell(t, money(item.totalEstimatedCost()), body);
            cell(t, text(item.totalPoles()), body);
            cell(t, text(item.totalElectricalLossesKw()), body);
            cell(t, money(item.landRowCompensationCost()), body);
        }
        return t;
    }

    // --- rendering helpers ------------------------------------------------

    private void section(Document document, String heading, Font font) {
        Paragraph p = new Paragraph(heading, font);
        p.setSpacingBefore(12);
        p.setSpacingAfter(6);
        document.add(p);
    }

    private Paragraph note(String body, Font font) {
        Paragraph p = new Paragraph(body, font);
        p.setSpacingAfter(6);
        return p;
    }

    private void addLabelled(PdfPTable table, String label, String value, Font labelFont, Font valueFont) {
        PdfPCell l = new PdfPCell(new Phrase(label, labelFont));
        l.setBorder(PdfPCell.NO_BORDER);
        l.setPadding(4);

        PdfPCell v = new PdfPCell(new Phrase(value, valueFont));
        v.setBorder(PdfPCell.NO_BORDER);
        v.setPadding(4);

        table.addCell(l);
        table.addCell(v);
    }

    private void header(PdfPTable table, String... titles) {
        Font font = FontFactory.getFont(FontFactory.HELVETICA_BOLD, 8, Color.WHITE);
        for (String title : titles) {
            PdfPCell cell = new PdfPCell(new Phrase(title, font));
            cell.setBackgroundColor(INK);
            cell.setHorizontalAlignment(Element.ALIGN_CENTER);
            cell.setPadding(5);
            table.addCell(cell);
        }
    }

    private void cell(PdfPTable table, String text, Font font) {
        PdfPCell cell = new PdfPCell(new Phrase(text != null ? text : "", font));
        cell.setPadding(3.5f);
        cell.setHorizontalAlignment(Element.ALIGN_CENTER);
        if (table.getRows().size() % 2 == 1) {
            cell.setBackgroundColor(BAND);
        }
        table.addCell(cell);
    }

    private void spanningNote(PdfPTable table, int columns, String message, Font font) {
        PdfPCell cell = new PdfPCell(new Phrase(message, font));
        cell.setColspan(columns);
        cell.setHorizontalAlignment(Element.ALIGN_CENTER);
        cell.setPadding(8);
        table.addCell(cell);
    }

    // --- formatting -------------------------------------------------------

    private static String text(Object value) {
        return value != null ? value.toString() : "—";
    }

    private static String unit(Object value, String unit) {
        return value != null ? value + " " + unit : "—";
    }

    private static String money(BigDecimal value) {
        return value != null ? "$" + value.setScale(2, RoundingMode.HALF_UP).toPlainString() : "—";
    }

    /** Scenario comparison carries its figures as doubles rather than BigDecimal. */
    private static String money(Double value) {
        return value != null ? money(BigDecimal.valueOf(value)) : "—";
    }

    private static String km(BigDecimal metres) {
        return metres != null
                ? metres.divide(BigDecimal.valueOf(1000), 3, RoundingMode.HALF_UP).toPlainString()
                : "—";
    }

    private static String coord(Double value) {
        return value != null ? String.format("%.6f", value) : "—";
    }
}
