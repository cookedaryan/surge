"""Builder for the canonical PY-036 Decision Report."""

from collections.abc import Iterable
from decimal import Decimal

from app.optimisation.workflow_models import (
    CandidateWorkflowResult,
    OptimisationStatus,
    OptimisationWorkflowResult,
    WorkflowStage,
)
from app.reporting.decision_models import (
    AlternativeStatus,
    AlternativeSummary,
    CandidateReference,
    ComparisonOutcome,
    DecisionFactor,
    DecisionReport,
    DecisionReportStatus,
    EconomicsSummary,
    ElectricalSummary,
    LandDecisionSummary,
    MetricDelta,
    MetricDirection,
    OptimizationEvidence,
    PhysicalSummary,
    PoleSummary,
    RecommendationReasoning,
    RecommendationSummary,
    RejectedCandidate,
    ReportProvenance,
    ReportWarning,
    ScoreSummary,
    SpatialSummary,
)


def _build_reference(candidate: CandidateWorkflowResult) -> CandidateReference:
    return CandidateReference(
        candidate_id=candidate.scenario.scenario_id,
        candidate_signature=candidate.scenario.topology_fingerprint,
        parent_candidate_id=candidate.scenario.lineage.parent_scenario_id
        if candidate.scenario.lineage
        else None,
        search_round=candidate.scenario.lineage.search_round
        if candidate.scenario.lineage
        else 0,
        mutation=candidate.scenario.lineage.mutation
        if candidate.scenario.lineage
        else None,
    )


def _build_physical_summary(
    candidate: CandidateWorkflowResult,
) -> PhysicalSummary | None:
    if (
        not candidate.engineering_assessment
        or not candidate.engineering_assessment.metrics
    ):
        return None
    metrics = candidate.engineering_assessment.metrics
    return PhysicalSummary(
        total_route_length_m=metrics.total_route_length_m,
        segment_count=candidate.scenario.network.segment_count,
    )


def _build_electrical_summary(
    candidate: CandidateWorkflowResult,
) -> ElectricalSummary | None:
    if not candidate.load_flow_result:
        return None
    lf = candidate.load_flow_result
    return ElectricalSummary(
        feasible=lf.is_valid,
        total_active_loss_mw=lf.total_active_loss_mw,
        maximum_loading_percent=lf.maximum_loading_percent,
        minimum_voltage_pu=lf.minimum_voltage_pu,
        maximum_voltage_pu=lf.maximum_voltage_pu,
        violation_count=len(lf.violations),
    )


def _build_spatial_summary(
    candidate: CandidateWorkflowResult,
) -> SpatialSummary | None:
    if not candidate.engineering_assessment:
        return None
    if not candidate.engineering_assessment.metrics:
        return None
    metrics = candidate.engineering_assessment.metrics
    return SpatialSummary(
        road_crossing_count=metrics.road_crossing_count,
        soft_constraint_overlap_length_m=metrics.soft_constraint_overlap_length_m,
        # Metrics wouldn't exist if hard exclusions were violated
        hard_exclusion_violation_count=0,
    )


def _build_land_summary(
    candidate: CandidateWorkflowResult,
) -> LandDecisionSummary | None:
    if not candidate.engineering_assessment:
        return None
    if not candidate.engineering_assessment.metrics:
        return None
    metrics = candidate.engineering_assessment.metrics
    return LandDecisionSummary(
        affected_parcels=metrics.affected_parcel_count,
        unique_owners=None,  # Not directly equivalent to owner interactions
        owner_interactions=metrics.owner_interaction_count,
    )


def _build_pole_summary(
    candidate: CandidateWorkflowResult,
) -> PoleSummary | None:
    if not candidate.presentation_result:
        return None
    if not candidate.presentation_result.pole_summary:
        return None

    # Extract micro-siting evidence if available
    # For now, we only have aggregate presentation summary which lacks specific moves.
    # In a full implementation, micro-siting report would be attached to candidate.
    ps = candidate.presentation_result.pole_summary
    return PoleSummary(
        total_poles=ps.total_poles,
        terminal_poles=ps.terminal_poles,
        angle_poles=ps.angle_poles,
        intermediate_poles=ps.intermediate_poles,
        junction_poles=ps.junction_poles,
        moved_poles=None,
        total_movement_m=None,
        micro_siting_moves=None,
    )


def _build_economics_summary(
    candidate: CandidateWorkflowResult,
) -> EconomicsSummary | None:
    if not candidate.cost_assessment:
        return None
    cost_assess = candidate.cost_assessment
    lifecycle = None
    if cost_assess.cost:
        lifecycle = cost_assess.cost.lifecycle_cost
    return EconomicsSummary(
        lifecycle_cost=lifecycle,
        conductor_capex=cost_assess.conductor_capex_amount,
        pole_capex=cost_assess.pole_capex_amount,
        land_capex=cost_assess.land_purchase_capex_amount,
        present_value_opex=cost_assess.present_value_opex_amount,
        currency=cost_assess.currency,
    )


def _build_score_summary(
    candidate: CandidateWorkflowResult,
) -> ScoreSummary | None:
    if not candidate.evaluation:
        return None
    ev = candidate.evaluation
    return ScoreSummary(
        engineering_benefit_score=ev.engineering_benefit_score,
        economic_benefit_score=ev.economic_benefit_score,
        final_benefit_score=ev.final_benefit_score,
        rank=ev.rank,
    )


def _calculate_delta(
    metric_name: str,
    recommended_val: float | int | Decimal | None,
    alternative_val: float | int | Decimal | None,
    direction: MetricDirection,
    unit: str | None = None,
) -> MetricDelta:
    abs_delta: Decimal | None = None
    rel_delta: float | None = None
    outcome: ComparisonOutcome | None = None

    if recommended_val is not None and alternative_val is not None:
        recommended_decimal = Decimal(str(recommended_val))
        alternative_decimal = Decimal(str(alternative_val))
        abs_delta = recommended_decimal - alternative_decimal
        epsilon = Decimal("1e-9")
        if abs(alternative_decimal) > epsilon:
            rel_delta = float(abs_delta / alternative_decimal)

        if direction == MetricDirection.LOWER_IS_BETTER:
            if abs_delta < -epsilon:
                outcome = ComparisonOutcome.BETTER
            elif abs_delta > epsilon:
                outcome = ComparisonOutcome.WORSE
            else:
                outcome = ComparisonOutcome.EQUAL
        elif direction == MetricDirection.HIGHER_IS_BETTER:
            if abs_delta > epsilon:
                outcome = ComparisonOutcome.BETTER
            elif abs_delta < -epsilon:
                outcome = ComparisonOutcome.WORSE
            else:
                outcome = ComparisonOutcome.EQUAL
        else:
            outcome = ComparisonOutcome.EQUAL if abs(abs_delta) < epsilon else None

    return MetricDelta(
        metric=metric_name,
        recommended_value=recommended_val,
        alternative_value=alternative_val,
        absolute_delta=abs_delta,
        relative_delta=rel_delta,
        preferred_direction=direction,
        outcome=outcome,
        unit=unit,
    )


def _build_comparisons(
    winner: CandidateWorkflowResult, alt: CandidateWorkflowResult
) -> tuple[MetricDelta, ...]:
    comparisons = []

    # 1. Total Route Length
    w_len = None
    a_len = None
    if winner.engineering_assessment and winner.engineering_assessment.metrics:
        w_len = winner.engineering_assessment.metrics.total_route_length_m
    if alt.engineering_assessment and alt.engineering_assessment.metrics:
        a_len = alt.engineering_assessment.metrics.total_route_length_m

    comparisons.append(
        _calculate_delta(
            "total_route_length_m", w_len, a_len, MetricDirection.LOWER_IS_BETTER, "m"
        )
    )

    # 2. Lifecycle Cost
    w_cost = None
    a_cost = None
    if winner.cost_assessment and winner.cost_assessment.cost:
        w_cost = winner.cost_assessment.cost.lifecycle_cost
    if alt.cost_assessment and alt.cost_assessment.cost:
        a_cost = alt.cost_assessment.cost.lifecycle_cost

    comparisons.append(
        _calculate_delta(
            "lifecycle_cost", w_cost, a_cost, MetricDirection.LOWER_IS_BETTER
        )
    )

    # 3. Parcel Count
    w_parcels = None
    a_parcels = None
    if winner.engineering_assessment and winner.engineering_assessment.metrics:
        w_parcels = winner.engineering_assessment.metrics.affected_parcel_count
    if alt.engineering_assessment and alt.engineering_assessment.metrics:
        a_parcels = alt.engineering_assessment.metrics.affected_parcel_count

    comparisons.append(
        _calculate_delta(
            "affected_parcels", w_parcels, a_parcels, MetricDirection.LOWER_IS_BETTER
        )
    )

    # 4. Total Active Loss
    w_loss = None
    a_loss = None
    if winner.load_flow_result:
        w_loss = winner.load_flow_result.total_active_loss_mw
    if alt.load_flow_result:
        a_loss = alt.load_flow_result.total_active_loss_mw

    comparisons.append(
        _calculate_delta(
            "total_active_loss_mw",
            w_loss,
            a_loss,
            MetricDirection.LOWER_IS_BETTER,
            "MW",
        )
    )

    # 5. Maximum Loading Percent
    w_load = None
    a_load = None
    if winner.load_flow_result:
        w_load = winner.load_flow_result.maximum_loading_percent
    if alt.load_flow_result:
        a_load = alt.load_flow_result.maximum_loading_percent

    comparisons.append(
        _calculate_delta(
            "maximum_loading_percent",
            w_load,
            a_load,
            MetricDirection.LOWER_IS_BETTER,
            "%",
        )
    )

    return tuple(comparisons)


def _build_reasoning(
    alternatives: Iterable[AlternativeSummary],
) -> RecommendationReasoning:
    advantages = []
    disadvantages = []

    # Compare against the closest alternative (rank 2) if it exists and is feasible
    feasible_alts = sorted(
        [
            a
            for a in alternatives
            if a.status == AlternativeStatus.FEASIBLE
            and a.scores
            and a.scores.rank is not None
        ],
        key=lambda a: a.scores.rank if a.scores and a.scores.rank else 999,
    )

    if feasible_alts:
        runner_up = feasible_alts[0]
        for delta in runner_up.comparisons:
            if delta.outcome == ComparisonOutcome.BETTER:
                sig = (
                    "primary"
                    if delta.metric in ("lifecycle_cost", "total_route_length_m")
                    else "secondary"
                )
                advantages.append(
                    DecisionFactor(
                        factor=delta.metric,
                        category="comparison",
                        comparison=delta,
                        significance=sig,
                    )
                )
            elif delta.outcome == ComparisonOutcome.WORSE:
                sig = (
                    "primary"
                    if delta.metric in ("lifecycle_cost", "total_route_length_m")
                    else "secondary"
                )
                disadvantages.append(
                    DecisionFactor(
                        factor=delta.metric,
                        category="comparison",
                        comparison=delta,
                        significance=sig,
                    )
                )

    return RecommendationReasoning(
        advantages=tuple(advantages),
        disadvantages=tuple(disadvantages),
        tradeoffs=(),
        alternative_decisions=(),
    )


def build_decision_report(
    result: OptimisationWorkflowResult, project_id: str
) -> DecisionReport:
    """Builds a deterministic DecisionReport from canonical optimization evidence."""

    # Build provenance
    # We look for the first cost assessment to extract catalogue details
    catalogue_id = None
    catalogue_version = None
    cost_model_version = None
    for c in result.candidates:
        if c.cost_assessment:
            catalogue_id = c.cost_assessment.catalogue_id
            catalogue_version = c.cost_assessment.catalogue_version
            cost_model_version = c.cost_assessment.cost_model_version
            break

    provenance = ReportProvenance(
        engineering_fingerprint=None,
        economic_fingerprint=None,
        catalogue_id=catalogue_id,
        catalogue_version=catalogue_version,
        cost_model_version=cost_model_version,
        search_enabled=True if result.search_result is not None else None,
        micro_siting_enabled=None,
    )

    # Identify winner
    winner = None
    if result.recommendation and result.recommendation.recommended_scenario_id:
        winner_id = result.recommendation.recommended_scenario_id
        for c in result.candidates:
            if c.scenario.scenario_id == winner_id:
                winner = c
                break

    if result.status == OptimisationStatus.FAILED:
        status = DecisionReportStatus.FAILED
    elif result.status == OptimisationStatus.PARTIAL_SUCCESS:
        status = DecisionReportStatus.INCOMPLETE
    elif not winner:
        status = DecisionReportStatus.NO_FEASIBLE_CANDIDATE
    else:
        status = DecisionReportStatus.SUCCESS

    if not winner:
        # FAILED or NO FEASIBLE CANDIDATE
        recommendation_summary = None
        alternatives: list[AlternativeSummary] = []
        rejected: list[RejectedCandidate] = []

        for c in result.candidates:
            ref = _build_reference(c)
            fail = c.execution_failure or c.pole_failure or c.packaging_failure
            if fail:
                rejected.append(
                    RejectedCandidate(
                        reference=ref,
                        failure_code=fail.code,
                        failure_stage=fail.stage,
                        message=fail.message,
                    )
                )
            elif not c.evaluation or not c.evaluation.assessment.eligible:
                msg = "Disqualified"
                codes: tuple[str, ...] = ()
                if c.evaluation and c.evaluation.assessment.disqualifications:
                    disqualifications = c.evaluation.assessment.disqualifications
                    codes = tuple(item.code.value for item in disqualifications)
                    msg = "; ".join(item.message for item in disqualifications)

                rejected.append(
                    RejectedCandidate(
                        reference=ref,
                        failure_code=codes[0] if codes else "DISQUALIFIED",
                        failure_stage=WorkflowStage.SCORING,
                        message=msg,
                        disqualification_codes=codes,
                    )
                )
            else:
                rejected.append(
                    RejectedCandidate(
                        reference=ref,
                        failure_code="UNKNOWN",
                        failure_stage="UNKNOWN",
                        message="Candidate rejected without explicit failure",
                    )
                )

        return DecisionReport(
            schema_version="1.0.0",
            status=status,
            project_id=project_id,
            optimisation_run_id=None,
            provenance=provenance,
            recommendation=recommendation_summary,
            alternatives=tuple(alternatives),
            rejected_candidates=tuple(rejected),
            warnings=tuple(
                ReportWarning(code=f.code, message=f.message) for f in result.failures
            ),
        )

    # Ensure physical, etc. are not None since this is the winner
    physical = _build_physical_summary(winner)
    electrical = _build_electrical_summary(winner)
    spatial = _build_spatial_summary(winner)
    land = _build_land_summary(winner)
    economics = _build_economics_summary(winner)
    scores = _build_score_summary(winner)

    if not (physical and electrical and spatial and land and scores):
        raise ValueError("Recommended candidate is missing required summaries")

    recommendation_summary = RecommendationSummary(
        reference=_build_reference(winner),
        physical=physical,
        electrical=electrical,
        spatial=spatial,
        land=land,
        poles=_build_pole_summary(winner),
        economics=economics,
        scores=scores,
    )

    alternatives = []
    rejected = []

    for c in result.candidates:
        if c.scenario.scenario_id == winner.scenario.scenario_id:
            continue

        ref = _build_reference(c)
        fail = c.execution_failure or c.pole_failure or c.packaging_failure

        if fail:
            rejected.append(
                RejectedCandidate(
                    reference=ref,
                    failure_code=fail.code,
                    failure_stage=fail.stage,
                    message=fail.message,
                )
            )
        elif not c.evaluation or not c.evaluation.assessment.eligible:
            # Technically failed evaluation, though maybe no execution failure
            # Distinguish based on disqualifications
            msg = "Disqualified"
            codes = ()
            if c.evaluation and c.evaluation.assessment.disqualifications:
                disqualifications = c.evaluation.assessment.disqualifications
                codes = tuple(item.code.value for item in disqualifications)
                msg = "; ".join(item.message for item in disqualifications)

            rejected.append(
                RejectedCandidate(
                    reference=ref,
                    failure_code=codes[0] if codes else "DISQUALIFIED",
                    failure_stage=WorkflowStage.SCORING,
                    message=msg,
                    disqualification_codes=codes,
                )
            )
        else:
            # Feasible alternative
            comparisons = _build_comparisons(winner, c)

            alternatives.append(
                AlternativeSummary(
                    reference=ref,
                    status=AlternativeStatus.FEASIBLE,
                    physical=_build_physical_summary(c),
                    electrical=_build_electrical_summary(c),
                    spatial=_build_spatial_summary(c),
                    land=_build_land_summary(c),
                    poles=_build_pole_summary(c),
                    economics=_build_economics_summary(c),
                    scores=_build_score_summary(c),
                    comparisons=comparisons,
                )
            )

    reasoning = _build_reasoning(alternatives)

    evidence = None
    if result.search_result:
        term_reason = None
        if hasattr(result.search_result.statistics, "termination_reason"):
            term_reason = result.search_result.statistics.termination_reason
        evidence = OptimizationEvidence(
            search_statistics=result.search_result.statistics,
            termination_reason=term_reason,
            winner_lineage=(),
        )

    warnings = tuple(
        ReportWarning(code=f.code, message=f.message) for f in result.failures
    )

    return DecisionReport(
        schema_version="1.0.0",
        status=status,
        project_id=project_id,
        optimisation_run_id=None,
        provenance=provenance,
        recommendation=recommendation_summary,
        alternatives=tuple(alternatives),
        rejected_candidates=tuple(rejected),
        reasoning=reasoning,
        optimization_evidence=evidence,
        warnings=warnings,
    )
