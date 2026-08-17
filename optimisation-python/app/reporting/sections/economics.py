from app.reporting.decision_models import DecisionReport
from app.reporting.sections.models import Metric, ReportSection, empty_section


def build_economics(report: DecisionReport) -> ReportSection:
    if not report.recommendation or not report.recommendation.economics:
        return empty_section("Economic Assessment", "No economic assessment available.")

    metrics = []
    econ = report.recommendation.economics

    if econ.currency:
        metrics.append(Metric("Currency", econ.currency))

    if econ.lifecycle_cost is not None:
        metrics.append(Metric("Lifecycle Cost", econ.lifecycle_cost))

    if econ.conductor_capex is not None:
        metrics.append(Metric("Conductor CAPEX", econ.conductor_capex))

    if econ.pole_capex is not None:
        metrics.append(Metric("Pole CAPEX", econ.pole_capex))

    if econ.land_capex is not None:
        metrics.append(Metric("Land CAPEX", econ.land_capex))

    if econ.present_value_opex is not None:
        metrics.append(Metric("Present Value OPEX", econ.present_value_opex))

    return ReportSection(
        title="Economic Assessment",
        summary=None,
        metrics=tuple(metrics),
        tables=(),
        notices=(),
        limitations=(),
    )
