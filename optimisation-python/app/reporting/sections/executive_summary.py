from app.reporting.decision_models import DecisionReport
from app.reporting.sections.models import Metric, ReportSection


def build_executive_summary(report: DecisionReport) -> ReportSection:
    metrics = []
    notices = []

    if report.recommendation:
        scores = report.recommendation.scores
        if scores.final_benefit_score is not None:
            metrics.append(
                Metric(
                    name="Final Benefit Score",
                    value=round(scores.final_benefit_score, 2),
                )
            )
        if scores.rank is not None:
            metrics.append(Metric(name="Rank", value=scores.rank))

    summary = (
        f"Engineering decision report for project {report.project_id}. "
        f"Status: {report.status.value}."
    )

    for warning in report.warnings:
        notices.append(f"[{warning.code}] {warning.message}")

    return ReportSection(
        title="Executive Summary",
        summary=summary,
        metrics=tuple(metrics),
        tables=(),
        notices=tuple(notices),
        limitations=(),
    )
