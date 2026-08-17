from app.reporting.decision_models import DecisionReport
from app.reporting.sections.models import Metric, ReportSection, empty_section


def build_electrical(report: DecisionReport) -> ReportSection:
    if not report.recommendation:
        return empty_section("Electrical Assessment", "No recommendation available.")

    metrics = []
    elec = report.recommendation.electrical

    metrics.append(Metric("Feasible", "Yes" if elec.feasible else "No"))

    if elec.total_active_loss_mw is not None:
        metrics.append(
            Metric("Total Active Loss (MW)", round(elec.total_active_loss_mw, 4))
        )

    if elec.maximum_loading_percent is not None:
        metrics.append(
            Metric("Maximum Loading (%)", round(elec.maximum_loading_percent, 2))
        )

    if elec.minimum_voltage_pu is not None:
        metrics.append(
            Metric("Minimum Voltage (pu)", round(elec.minimum_voltage_pu, 4))
        )

    if elec.maximum_voltage_pu is not None:
        metrics.append(
            Metric("Maximum Voltage (pu)", round(elec.maximum_voltage_pu, 4))
        )

    if elec.violation_count is not None:
        metrics.append(Metric("Violation Count", elec.violation_count))

    return ReportSection(
        title="Electrical Assessment",
        summary=None,
        metrics=tuple(metrics),
        tables=(),
        notices=(),
        limitations=(),
    )
