from app.reporting.decision_models import DecisionReport
from app.reporting.sections.models import ReportSection, Table


def build_alternatives(report: DecisionReport) -> ReportSection:
    tables = []

    # Alternatives
    if report.alternatives:
        alt_headers = (
            "Candidate ID",
            "Status",
            "Total Route Length (m)",
            "Final Benefit Score",
        )
        alt_rows = []
        for alt in report.alternatives:
            length = alt.physical.total_route_length_m if alt.physical else "N/A"
            score = (
                round(alt.scores.final_benefit_score, 2)
                if alt.scores and alt.scores.final_benefit_score is not None
                else "N/A"
            )
            alt_rows.append(
                (alt.reference.candidate_id, alt.status.value, length, score)
            )
        tables.append(
            Table(
                title="Feasible Alternatives", headers=alt_headers, rows=tuple(alt_rows)
            )
        )

        # Comparisons
        comp_headers = (
            "Candidate ID",
            "Metric",
            "Recommended",
            "Alternative",
            "Delta",
            "Outcome",
        )
        comp_rows = []
        for alt in report.alternatives:
            for comp in alt.comparisons:
                comp_rows.append(
                    (
                        alt.reference.candidate_id,
                        comp.metric,
                        str(comp.recommended_value)
                        if comp.recommended_value is not None
                        else "N/A",
                        str(comp.alternative_value)
                        if comp.alternative_value is not None
                        else "N/A",
                        str(comp.absolute_delta)
                        if comp.absolute_delta is not None
                        else "N/A",
                        comp.outcome.value if comp.outcome else "N/A",
                    )
                )
        if comp_rows:
            tables.append(
                Table(
                    title="Alternative Comparisons",
                    headers=comp_headers,
                    rows=tuple(comp_rows),
                )
            )

    # Rejected Candidates
    if report.rejected_candidates:
        rej_headers = ("Candidate ID", "Failure Stage", "Failure Code", "Message")
        rej_rows = []
        for rej in report.rejected_candidates:
            rej_rows.append(
                (
                    rej.reference.candidate_id,
                    rej.failure_stage
                    if isinstance(rej.failure_stage, str)
                    else rej.failure_stage.value,
                    rej.failure_code
                    if isinstance(rej.failure_code, str)
                    else rej.failure_code.value,
                    rej.message,
                )
            )
        tables.append(
            Table(
                title="Rejected Candidates", headers=rej_headers, rows=tuple(rej_rows)
            )
        )

    summary = (
        "Comparison with alternative candidates and rejected options."
        if tables
        else "No alternatives or rejected candidates reported."
    )

    return ReportSection(
        title="Alternatives",
        summary=summary,
        metrics=(),
        tables=tuple(tables),
        notices=(),
        limitations=(),
    )
