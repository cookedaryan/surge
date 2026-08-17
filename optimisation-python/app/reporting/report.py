from dataclasses import dataclass

from app.reporting.decision_models import DecisionReport
from app.reporting.sections import (
    alternatives,
    economics,
    electrical,
    executive_summary,
    land,
    reasoning,
    recommendation,
    traceability,
)
from app.reporting.sections.models import ReportSection


@dataclass(frozen=True)
class EngineeringReport:
    sections: list[ReportSection]
    limitations: list[str]


def build_engineering_report(report: DecisionReport) -> EngineeringReport:
    """Builds the final engineering report sections from a DecisionReport."""
    sections = [
        executive_summary.build_executive_summary(report),
        recommendation.build_recommendation(report),
        electrical.build_electrical(report),
        land.build_land(report),
        economics.build_economics(report),
        alternatives.build_alternatives(report),
        reasoning.build_reasoning(report),
        traceability.build_traceability(report),
    ]

    # Roll up limitations from all sections
    limitations = []
    for section in sections:
        for lim in section.limitations:
            if lim not in limitations:
                limitations.append(lim)

    return EngineeringReport(sections=sections, limitations=limitations)
