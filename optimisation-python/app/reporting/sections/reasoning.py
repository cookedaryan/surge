from collections.abc import Iterable

from app.reporting.decision_models import DecisionFactor, DecisionReport
from app.reporting.sections.models import ReportSection, Table


def build_reasoning(report: DecisionReport) -> ReportSection:
    tables = []

    if not report.reasoning:
        return ReportSection(
            title="Optimization Reasoning",
            summary=None,
            metrics=(),
            tables=(),
            notices=(),
            limitations=(),
        )

    reasoning = report.reasoning

    def _add_factors_table(title: str, factors: Iterable[DecisionFactor]) -> None:
        if not factors:
            return
        headers = ("Factor", "Category", "Comparison Metric", "Delta", "Significance")
        rows = []
        for factor in factors:
            delta = factor.comparison.absolute_delta
            rows.append(
                (
                    factor.factor,
                    factor.category,
                    factor.comparison.metric,
                    str(delta) if delta is not None else "N/A",
                    factor.significance,
                )
            )
        tables.append(Table(title=title, headers=headers, rows=tuple(rows)))

    _add_factors_table("Advantages", reasoning.advantages)
    _add_factors_table("Disadvantages", reasoning.disadvantages)

    # tradeoffs and alternative_decisions might be empty, so omit cleanly
    if reasoning.tradeoffs:
        _add_factors_table("Tradeoffs", reasoning.tradeoffs)

    if reasoning.alternative_decisions:
        headers = ("Decision",)
        rows = [(d,) for d in reasoning.alternative_decisions]
        tables.append(
            Table(title="Alternative Decisions", headers=headers, rows=tuple(rows))
        )

    return ReportSection(
        title="Optimization Reasoning",
        summary=None,
        metrics=(),
        tables=tuple(tables),
        notices=(),
        limitations=(),
    )
