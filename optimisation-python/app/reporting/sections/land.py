from app.reporting.decision_models import DecisionReport
from app.reporting.sections.models import Metric, ReportSection, empty_section


def build_land(report: DecisionReport) -> ReportSection:
    if not report.recommendation:
        return empty_section("Land & Commercial", "No recommendation available.")

    metrics = []
    limitations = []
    land_summary = report.recommendation.land

    metrics.append(Metric("Affected Parcels", land_summary.affected_parcels))
    metrics.append(Metric("Owner Interactions", land_summary.owner_interactions))

    if land_summary.unique_owners is not None:
        metrics.append(Metric("Unique Owners", land_summary.unique_owners))
    else:
        # NOT_AVAILABLE rule applied per field
        metrics.append(Metric("Unique Owners", "Not available"))
        limitations.append(
            "Unique Owners value is not available in the upstream decision report."
        )

    return ReportSection(
        title="Land & Commercial",
        summary=None,
        metrics=tuple(metrics),
        tables=(),
        notices=(),
        limitations=tuple(limitations),
    )
