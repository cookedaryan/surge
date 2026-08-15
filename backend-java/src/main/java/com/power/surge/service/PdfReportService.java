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
import com.power.surge.dto.report.ScenarioComparisonResponse;
import com.power.surge.dto.report.ScenarioSummaryItem;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.awt.Color;
import java.io.ByteArrayOutputStream;
import java.time.Instant;
import java.time.ZoneId;
import java.time.format.DateTimeFormatter;
import java.util.UUID;

@Service
@Transactional(readOnly = true)
public class PdfReportService {

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

    public byte[] generateExecutivePdfReport(UUID projectId) {
        ProjectResponse project = projectService.getProject(projectId);
        auditLogService.record("REPORT_EXPORTED", "PROJECT", projectId.toString(),
                "Exported executive PDF report for project '" + project.name() + "'");
        EngineeringBomReportResponse bomReport = reportService.generateBomReport(projectId, null);
        ScenarioComparisonResponse scenarioResponse = reportService.getScenarioComparison(projectId);

        ByteArrayOutputStream out = new ByteArrayOutputStream();
        Document document = new Document(PageSize.A4, 36, 36, 36, 36);

        try {
            PdfWriter.getInstance(document, out);
            document.open();

            // Fonts
            Font titleFont = FontFactory.getFont(FontFactory.HELVETICA_BOLD, 18, new Color(15, 23, 42));
            Font subTitleFont = FontFactory.getFont(FontFactory.HELVETICA_BOLD, 12, new Color(59, 130, 246));
            Font sectionFont = FontFactory.getFont(FontFactory.HELVETICA_BOLD, 13, new Color(30, 41, 59));
            Font boldFont = FontFactory.getFont(FontFactory.HELVETICA_BOLD, 9, Color.BLACK);
            Font regularFont = FontFactory.getFont(FontFactory.HELVETICA, 9, Color.DARK_GRAY);
            Font smallMuted = FontFactory.getFont(FontFactory.HELVETICA, 8, Color.GRAY);

            // Title Banner
            Paragraph title = new Paragraph("SURGE 33 kV POWER EVACUATION EXECUTIVE REPORT", titleFont);
            title.setAlignment(Element.ALIGN_CENTER);
            document.add(title);

            Paragraph sub = new Paragraph("Smart Utility Routing & Grid Evacuation Spatial Evacuation Plan", subTitleFont);
            sub.setAlignment(Element.ALIGN_CENTER);
            sub.setSpacingAfter(15);
            document.add(sub);

            // Metadata Table
            PdfPTable metaTable = new PdfPTable(2);
            metaTable.setWidthPercentage(100);
            metaTable.setSpacingAfter(15);

            addTableCell(metaTable, "Project Name:", project.name(), boldFont, regularFont);
            addTableCell(metaTable, "Project ID:", project.id().toString(), boldFont, regularFont);
            addTableCell(metaTable, "Coordinate Reference System:", project.crs(), boldFont, regularFont);
            addTableCell(metaTable, "Report Generation Time:", DateTimeFormatter.ISO_OFFSET_DATE_TIME.format(Instant.now().atZone(ZoneId.of("UTC"))), boldFont, regularFont);

            document.add(metaTable);

            // Section 1: Executive Summary & Overall Capex
            Paragraph sec1 = new Paragraph("1. Executive Summary & Infrastructure Totals", sectionFont);
            sec1.setSpacingBefore(10);
            sec1.setSpacingAfter(8);
            document.add(sec1);

            PdfPTable summaryTable = new PdfPTable(4);
            summaryTable.setWidthPercentage(100);
            summaryTable.setSpacingAfter(15);

            addHeaderCell(summaryTable, "Total Length (km)");
            addHeaderCell(summaryTable, "Pole Count");
            addHeaderCell(summaryTable, "Estimated CAPEX ($)");
            addHeaderCell(summaryTable, "Electrical Losses (kW)");

            double totalKm = bomReport != null && bomReport.totalNetworkLengthMeters() != null ? bomReport.totalNetworkLengthMeters().doubleValue() / 1000.0 : 0.0;
            int totalPoles = bomReport != null && bomReport.totalPoles() != null ? bomReport.totalPoles() : 0;
            String costStr = bomReport != null && bomReport.totalEstimatedCost() != null ? "$" + bomReport.totalEstimatedCost().toString() : "$0.00";
            String lossStr = bomReport != null && bomReport.totalElectricalLossesKw() != null ? bomReport.totalElectricalLossesKw().toString() + " kW" : "0.0 kW";

            addContentCell(summaryTable, String.format("%.2f km", totalKm), regularFont);
            addContentCell(summaryTable, String.valueOf(totalPoles), regularFont);
            addContentCell(summaryTable, costStr, regularFont);
            addContentCell(summaryTable, lossStr, regularFont);

            document.add(summaryTable);

            // Section 2: Bill of Materials Feeder Breakdown
            Paragraph sec2 = new Paragraph("2. Feeder Schedule & Bill of Materials (BOM)", sectionFont);
            sec2.setSpacingBefore(10);
            sec2.setSpacingAfter(8);
            document.add(sec2);

            PdfPTable bomTable = new PdfPTable(5);
            bomTable.setWidthPercentage(100);
            bomTable.setWidths(new float[]{2.5f, 1.5f, 1.2f, 1.8f, 1.8f});
            bomTable.setSpacingAfter(15);

            addHeaderCell(bomTable, "Feeder Name");
            addHeaderCell(bomTable, "Length (km)");
            addHeaderCell(bomTable, "Poles");
            addHeaderCell(bomTable, "Losses (kW)");
            addHeaderCell(bomTable, "Est. Cost ($)");

            if (bomReport != null && bomReport.feederSummaries() != null && !bomReport.feederSummaries().isEmpty()) {
                for (FeederBomSummary feeder : bomReport.feederSummaries()) {
                    addContentCell(bomTable, feeder.feederName(), regularFont);
                    addContentCell(bomTable, String.format("%.2f", feeder.lengthMeters().doubleValue() / 1000.0), regularFont);
                    addContentCell(bomTable, String.valueOf(feeder.poleCount()), regularFont);
                    addContentCell(bomTable, feeder.electricalLossesKw().toString(), regularFont);
                    addContentCell(bomTable, "$" + feeder.totalCost().toString(), regularFont);
                }
            } else {
                PdfPCell emptyCell = new PdfPCell(new Phrase("No feeder routes generated for project.", regularFont));
                emptyCell.setColspan(5);
                emptyCell.setHorizontalAlignment(Element.ALIGN_CENTER);
                bomTable.addCell(emptyCell);
            }

            document.add(bomTable);

            // Section 3: Multi-Scenario Analytics Matrix
            Paragraph sec3 = new Paragraph("3. Multi-Scenario Optimization Matrix", sectionFont);
            sec3.setSpacingBefore(10);
            sec3.setSpacingAfter(8);
            document.add(sec3);

            PdfPTable scenarioTable = new PdfPTable(5);
            scenarioTable.setWidthPercentage(100);
            scenarioTable.setWidths(new float[]{2.2f, 1.8f, 1.5f, 1.8f, 1.8f});
            scenarioTable.setSpacingAfter(20);

            addHeaderCell(scenarioTable, "Scenario Objective");
            addHeaderCell(scenarioTable, "CAPEX ($)");
            addHeaderCell(scenarioTable, "Poles");
            addHeaderCell(scenarioTable, "Losses (kW)");
            addHeaderCell(scenarioTable, "ROW Cost ($)");

            if (scenarioResponse != null && scenarioResponse.scenarios() != null) {
                for (ScenarioSummaryItem item : scenarioResponse.scenarios()) {
                    addContentCell(scenarioTable, item.scenarioName(), boldFont);
                    addContentCell(scenarioTable, "$" + item.totalEstimatedCost().toString(), regularFont);
                    addContentCell(scenarioTable, String.valueOf(item.totalPoles()), regularFont);
                    addContentCell(scenarioTable, item.totalElectricalLossesKw().toString(), regularFont);
                    addContentCell(scenarioTable, "$" + item.landRowCompensationCost().toString(), regularFont);
                }
            }

            document.add(scenarioTable);

            // Footer sign-off
            Paragraph footer = new Paragraph("Generated by SURGE Engine — Confidential Engineering Evacuation Plan", smallMuted);
            footer.setAlignment(Element.ALIGN_CENTER);
            document.add(footer);

            document.close();

        } catch (Exception e) {
            throw new RuntimeException("Failed to generate executive PDF report: " + e.getMessage(), e);
        }

        return out.toByteArray();
    }

    private void addTableCell(PdfPTable table, String label, String value, Font labelFont, Font valFont) {
        PdfPCell cell1 = new PdfPCell(new Phrase(label, labelFont));
        cell1.setBorder(PdfPCell.NO_BORDER);
        cell1.setPadding(4);

        PdfPCell cell2 = new PdfPCell(new Phrase(value, valFont));
        cell2.setBorder(PdfPCell.NO_BORDER);
        cell2.setPadding(4);

        table.addCell(cell1);
        table.addCell(cell2);
    }

    private void addHeaderCell(PdfPTable table, String text) {
        Font font = FontFactory.getFont(FontFactory.HELVETICA_BOLD, 9, Color.WHITE);
        PdfPCell cell = new PdfPCell(new Phrase(text, font));
        cell.setBackgroundColor(new Color(15, 23, 42));
        cell.setHorizontalAlignment(Element.ALIGN_CENTER);
        cell.setPadding(6);
        table.addCell(cell);
    }

    private void addContentCell(PdfPTable table, String text, Font font) {
        PdfPCell cell = new PdfPCell(new Phrase(text, font));
        cell.setPadding(5);
        cell.setHorizontalAlignment(Element.ALIGN_CENTER);
        table.addCell(cell);
    }
}
