from app.reporting.decision_models import DecisionReport
from app.reporting.limitations import REPORT_SCHEMA_LIMITATIONS
from app.reporting.sections.models import Metric, ReportSection, empty_section


def build_recommendation(report: DecisionReport) -> ReportSection:
    if not report.recommendation:
        return empty_section("Recommended Design", "No recommendation available.")

    metrics = []
    limitations = []
    rec = report.recommendation

    # Candidate Identity
    metrics.append(Metric("Candidate ID", rec.reference.candidate_id))
    metrics.append(Metric("Candidate Signature", rec.reference.candidate_signature))

    # Physical
    metrics.append(Metric("Total Route Length (m)", rec.physical.total_route_length_m))
    metrics.append(Metric("Segment Count", rec.physical.segment_count))

    # Poles
    if rec.poles:
        metrics.append(Metric("Total Poles", rec.poles.total_poles))
        metrics.append(Metric("Terminal Poles", rec.poles.terminal_poles))
        metrics.append(Metric("Angle Poles", rec.poles.angle_poles))
        metrics.append(Metric("Intermediate Poles", rec.poles.intermediate_poles))
        metrics.append(Metric("Junction Poles", rec.poles.junction_poles))

    # Spatial
    metrics.append(Metric("Road Crossings", rec.spatial.road_crossing_count))
    metrics.append(
        Metric(
            "Soft-constraint Overlap (m)", rec.spatial.soft_constraint_overlap_length_m
        )
    )

    # Check schema limitations for hard exclusions
    schema_limitations = REPORT_SCHEMA_LIMITATIONS.get(report.schema_version, {})
    if "spatial.hard_exclusion_violation_count" in schema_limitations:
        limitations.append(
            "Hard-exclusion compliance count is not reported — current upstream value is not derived from materialized constraint evidence."
        )
    else:
        metrics.append(
            Metric(
                "Hard-exclusion Violations", rec.spatial.hard_exclusion_violation_count
            )
        )

    return ReportSection(
        title="Recommended Design",
        summary=None,
        metrics=tuple(metrics),
        tables=(),
        notices=(),
        limitations=tuple(limitations),
    )
