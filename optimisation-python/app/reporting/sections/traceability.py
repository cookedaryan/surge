from app.reporting.decision_models import DecisionReport
from app.reporting.sections.models import Metric, ReportSection, Table


def build_traceability(report: DecisionReport) -> ReportSection:
    metrics = []
    tables = []

    prov = report.provenance
    if prov:
        if prov.engineering_fingerprint:
            metrics.append(
                Metric("Engineering Fingerprint", prov.engineering_fingerprint)
            )
        if prov.economic_fingerprint:
            metrics.append(Metric("Economic Fingerprint", prov.economic_fingerprint))
        if prov.catalogue_id:
            metrics.append(Metric("Catalogue ID", prov.catalogue_id))
        if prov.catalogue_version:
            metrics.append(Metric("Catalogue Version", prov.catalogue_version))
        if prov.cost_model_version:
            metrics.append(Metric("Cost Model Version", prov.cost_model_version))
        if prov.search_enabled is not None:
            metrics.append(
                Metric("Search Enabled", "Yes" if prov.search_enabled else "No")
            )
        if prov.micro_siting_enabled is not None:
            metrics.append(
                Metric(
                    "Micro-siting Enabled", "Yes" if prov.micro_siting_enabled else "No"
                )
            )

        metrics.append(Metric("Report Schema Version", prov.report_schema_version))

    # optimisation_run_id omitted per NOT_REPORTED rule if None.
    if report.optimisation_run_id is not None:
        metrics.append(Metric("Optimisation Run ID", report.optimisation_run_id))

    if report.optimization_evidence:
        evidence = report.optimization_evidence

        if evidence.termination_reason:
            metrics.append(
                Metric("Search Termination Reason", evidence.termination_reason.value)
            )

        if evidence.search_statistics:
            stats = evidence.search_statistics
            total_evals = (
                stats.search_evaluations_used + stats.evaluation_cache_hit_count
            )
            metrics.append(Metric("Total Candidates Evaluated", total_evals))
            metrics.append(Metric("Feasible Candidates Found", stats.feasible_count))

        # winner_lineage omitted if empty
        if evidence.winner_lineage:
            headers = ("Search Round", "Candidate ID", "Parent ID", "Mutation")
            rows = []
            for lin in evidence.winner_lineage:
                mutation_str = lin.mutation.operator if lin.mutation else "N/A"
                rows.append(
                    (
                        lin.search_round,
                        lin.candidate_id,
                        lin.parent_candidate_id if lin.parent_candidate_id else "N/A",
                        mutation_str,
                    )
                )
            tables.append(
                Table(title="Winner Lineage", headers=headers, rows=tuple(rows))
            )

    return ReportSection(
        title="Traceability",
        summary=None,
        metrics=tuple(metrics),
        tables=tuple(tables),
        notices=(),
        limitations=(),
    )
