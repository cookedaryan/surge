"""Multi-objective scoring and recommendation pipeline."""

import hashlib
import json
import math
from dataclasses import replace

from app.costing.models import CandidateCostAssessment
from app.optimisation.engineering_metric_models import CandidateEngineeringMetrics
from app.optimisation.scenario_models import ScenarioStrategy
from app.optimisation.scoring_models import (
    CandidateAssessment,
    CandidateEvaluation,
    CandidateScoringConfig,
    CostAwareRecommendationConfig,
    Disqualification,
    DisqualificationCode,
    EngineeringEvaluatedScenario,
    GroupScore,
    MetricComparison,
    MetricScore,
    NormalizationRange,
    OptimizationRecommendation,
    OptimizationRecommendationStatus,
    RecommendationReason,
    RecommendationReasonCode,
    ScoringGroup,
    ScoringMetric,
    ScoringPolicyMode,
)

SCORE_COMPARISON_DECIMALS = 12


def compute_economic_context_id(assessment: CandidateCostAssessment) -> str:
    cost = assessment.cost
    if cost is None:
        raise ValueError("A complete lifecycle cost is required")
    state = {
        "currency": cost.currency,
        "catalogue_id": cost.catalogue_id,
        "catalogue_version": cost.catalogue_version,
        "catalogue_price_basis_date": cost.catalogue_price_basis_date.isoformat(),
        "energy_price_basis_date": cost.energy_price_basis_date.isoformat(),
        "cost_model_version": cost.cost_model_version,
        "analysis_period_years": cost.analysis_period_years,
        "discount_rate": str(cost.discount_rate.normalize()),
        "annual_operating_hours": cost.annual_operating_hours,
        "loss_load_factor": str(cost.loss_load_factor.normalize()),
        "energy_price_per_mwh": str(cost.energy_price_per_mwh.normalize()),
    }
    serialized = json.dumps(state, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(serialized.encode("utf-8")).hexdigest()


def extract_candidate_assessment(
    wrapper: EngineeringEvaluatedScenario,
) -> CandidateAssessment:
    scenario = wrapper.electrical.scenario
    result = wrapper.electrical.load_flow_result
    engineering = wrapper.engineering_assessment
    disqualifications: list[Disqualification] = []
    if not result.converged:
        disqualifications.append(
            Disqualification(
                code=DisqualificationCode.LOAD_FLOW_NOT_CONVERGED,
                message="Load flow did not converge",
            )
        )
    elif not result.is_valid or result.violations:
        disqualifications.append(
            Disqualification(
                code=DisqualificationCode.ELECTRICAL_VIOLATION,
                message="Candidate contains electrical violations or is marked invalid",
                underlying_violations=tuple(
                    sorted({violation.code for violation in result.violations})
                ),
            )
        )

    network = scenario.network
    if (
        len(result.buses) != network.wtg_count + 1
        or len(result.segments) != network.segment_count
        or len(result.feeders) != network.feeder_count
    ):
        disqualifications.append(
            Disqualification(
                code=DisqualificationCode.TOPOLOGY_MISMATCH,
                message="Load-flow result shape does not match the candidate network",
            )
        )

    if not engineering.engineering_metrics_available:
        disqualifications.append(
            Disqualification(
                code=DisqualificationCode.ENGINEERING_METRICS_UNAVAILABLE,
                message="Canonical engineering metrics could not be extracted",
                underlying_violations=tuple(
                    failure.code for failure in engineering.extraction_failures
                ),
            )
        )
    if engineering.hard_violation_ids:
        disqualifications.append(
            Disqualification(
                code=DisqualificationCode.HARD_SPATIAL_VIOLATION,
                message="Candidate intersects hard avoidance constraints",
                underlying_violations=engineering.hard_violation_ids,
            )
        )
    return CandidateAssessment(
        scenario_id=engineering.scenario_id,
        eligible=not disqualifications,
        disqualifications=tuple(disqualifications),
        metrics=engineering.metrics,
    )


def _get_raw(metrics: CandidateEngineeringMetrics, metric: ScoringMetric) -> float:
    if metric == ScoringMetric.ROUTE_LENGTH:
        return metrics.total_route_length_m
    if metric == ScoringMetric.TRAVERSAL_COST:
        return metrics.total_traversal_cost
    if metric == ScoringMetric.AFFECTED_PARCEL_COUNT:
        return float(metrics.affected_parcel_count)
    if metric == ScoringMetric.ROAD_CROSSING_COUNT:
        return float(metrics.road_crossing_count)
    if metric == ScoringMetric.SOFT_CONSTRAINT_OVERLAP_LENGTH:
        return metrics.soft_constraint_overlap_length_m
    if metric == ScoringMetric.PHYSICAL_POLE_COUNT:
        return float(metrics.physical_pole_count)
    if metric == ScoringMetric.ACTIVE_LOSS:
        return metrics.total_active_loss_mw
    if metric == ScoringMetric.CABLE_LOADING:
        return metrics.maximum_loading_percent
    if metric == ScoringMetric.VOLTAGE_MARGIN:
        return metrics.voltage_margin_pu
    raise ValueError(f"Unknown metric {metric}")


def compute_normalization_ranges(
    eligible_assessments: list[CandidateAssessment],
) -> tuple[NormalizationRange, ...]:
    if not eligible_assessments:
        return ()
    ranges: list[NormalizationRange] = []
    for metric in ScoringMetric:
        values = []
        for assessment in eligible_assessments:
            if assessment.metrics is None:
                raise ValueError("Eligible candidate is missing engineering metrics")
            values.append(_get_raw(assessment.metrics, metric))
        minimum = min(values)
        maximum = max(values)
        ranges.append(
            NormalizationRange(
                metric=metric,
                minimum=minimum,
                maximum=maximum,
                constant=minimum == maximum,
            )
        )
    return tuple(ranges)


def normalize_metric_benefit(raw_value: float, norm_range: NormalizationRange) -> float:
    if norm_range.constant:
        return 0.0
    if norm_range.metric == ScoringMetric.VOLTAGE_MARGIN:
        normalized = (raw_value - norm_range.minimum) / (
            norm_range.maximum - norm_range.minimum
        )
    else:
        normalized = (norm_range.maximum - raw_value) / (
            norm_range.maximum - norm_range.minimum
        )
    return max(0.0, min(1.0, normalized))


def _get_metric_group(metric: ScoringMetric) -> ScoringGroup:
    if metric == ScoringMetric.ROUTE_LENGTH:
        return ScoringGroup.PHYSICAL
    if metric in {
        ScoringMetric.TRAVERSAL_COST,
        ScoringMetric.AFFECTED_PARCEL_COUNT,
        ScoringMetric.ROAD_CROSSING_COUNT,
        ScoringMetric.SOFT_CONSTRAINT_OVERLAP_LENGTH,
    }:
        return ScoringGroup.SPATIAL
    if metric == ScoringMetric.PHYSICAL_POLE_COUNT:
        return ScoringGroup.INFRASTRUCTURE
    return ScoringGroup.ELECTRICAL


def _get_group_weight(group: ScoringGroup, config: CandidateScoringConfig) -> float:
    if group == ScoringGroup.PHYSICAL:
        return config.physical_weight
    if group == ScoringGroup.SPATIAL:
        return config.spatial_weight
    if group == ScoringGroup.INFRASTRUCTURE:
        return config.infrastructure_weight
    return config.electrical_weight


def _get_metric_subweight(
    metric: ScoringMetric,
    config: CandidateScoringConfig,
) -> float:
    if metric in {ScoringMetric.ROUTE_LENGTH, ScoringMetric.PHYSICAL_POLE_COUNT}:
        return 1.0
    spatial = config.spatial_subweights
    electrical = config.electrical_subweights
    return {
        ScoringMetric.TRAVERSAL_COST: spatial.traversal_cost,
        ScoringMetric.AFFECTED_PARCEL_COUNT: spatial.affected_parcels,
        ScoringMetric.ROAD_CROSSING_COUNT: spatial.road_crossings,
        ScoringMetric.SOFT_CONSTRAINT_OVERLAP_LENGTH: spatial.soft_overlap_length,
        ScoringMetric.ACTIVE_LOSS: electrical.active_loss,
        ScoringMetric.CABLE_LOADING: electrical.cable_loading,
        ScoringMetric.VOLTAGE_MARGIN: electrical.voltage_margin,
    }[metric]


def evaluate_cohort(
    wrappers: tuple[EngineeringEvaluatedScenario, ...],
    scoring_config: CandidateScoringConfig,
    cost_assessments: dict[str, CandidateCostAssessment] | None = None,
    cost_aware_config: CostAwareRecommendationConfig | None = None,
) -> OptimizationRecommendation:
    """Evaluate, score, and rank a set of completely evaluated PNC scenarios."""
    if not wrappers:
        raise ValueError("Must provide at least one candidate for scoring")

    comp_group_id = wrappers[0].electrical.scenario.comparison_group_id
    elec_context_id = wrappers[0].electrical.electrical_context_id
    seen_ids = set()
    seen_fps = set()

    for w in wrappers:
        if w.electrical.scenario.comparison_group_id != comp_group_id:
            raise ValueError("All candidates must share the same comparison_group_id")
        if w.electrical.electrical_context_id != elec_context_id:
            raise ValueError("All candidates must share the same electrical_context_id")

        sid = w.electrical.scenario.scenario_id
        if sid in seen_ids:
            raise ValueError(f"Duplicate scenario_id: {sid}")
        seen_ids.add(sid)

        fp = w.electrical.scenario.topology_fingerprint
        if fp in seen_fps:
            raise ValueError(f"Duplicate topology_fingerprint: {fp}")
        seen_fps.add(fp)

    is_cost_aware = scoring_config.policy_mode == ScoringPolicyMode.COST_AWARE
    if is_cost_aware and cost_aware_config is None:
        raise ValueError("cost_aware_config must be provided for COST_AWARE mode")

    assessments = [extract_candidate_assessment(w) for w in wrappers]

    economic_context_id: str | None = None
    candidate_costs: dict[str, float] = {}
    complete_cost_assessments: dict[str, CandidateCostAssessment] = {}

    if is_cost_aware:
        economic_contexts: set[str] = set()
        for index, (wrapper, assessment) in enumerate(
            zip(wrappers, assessments, strict=True)
        ):
            scenario_id = assessment.scenario_id
            cost_assessment = wrapper.cost_assessment
            if cost_assessment is None and cost_assessments is not None:
                cost_assessment = cost_assessments.get(scenario_id)
            if cost_assessment is None or cost_assessment.cost is None:
                assessments[index] = replace(
                    assessment,
                    eligible=False,
                    disqualifications=assessment.disqualifications
                    + (
                        Disqualification(
                            code=DisqualificationCode.INCOMPLETE_LIFECYCLE_COST,
                            message=(
                                "Lifecycle cost assessment is missing or incomplete"
                            ),
                        ),
                    ),
                )
                continue

            if cost_assessment.scenario_id != scenario_id:
                raise ValueError(
                    "Cost assessment scenario_id must match the evaluated scenario"
                )
            if cost_assessment.cost.scenario_id != scenario_id:
                raise ValueError(
                    "Lifecycle cost scenario_id must match the evaluated scenario"
                )
            complete_cost_assessments[scenario_id] = cost_assessment
            candidate_costs[scenario_id] = float(
                cost_assessment.cost.lifecycle_cost
            )
            if assessment.eligible:
                economic_contexts.add(
                    compute_economic_context_id(cost_assessment)
                )

        if len(economic_contexts) == 1:
            economic_context_id = next(iter(economic_contexts))
        elif len(economic_contexts) > 1:
            mismatch = Disqualification(
                code=DisqualificationCode.ECONOMIC_CONTEXT_MISMATCH,
                message=(
                    "Lifecycle costs use different economic contexts and cannot "
                    "be compared"
                ),
            )
            assessments = [
                replace(
                    assessment,
                    eligible=False,
                    disqualifications=assessment.disqualifications + (mismatch,),
                )
                if assessment.eligible
                else assessment
                for assessment in assessments
            ]

    eligible_assessments = [a for a in assessments if a.eligible]

    ranges_tuple = compute_normalization_ranges(eligible_assessments)
    ranges_dict = {r.metric: r for r in ranges_tuple}

    min_cost: float | None = None
    max_cost: float | None = None
    if is_cost_aware and eligible_assessments:
        costs = [candidate_costs[a.scenario_id] for a in eligible_assessments]
        min_cost = min(costs)
        max_cost = max(costs)

    evaluations: list[CandidateEvaluation] = []

    lowest_cost_sid = None

    for a in assessments:
        if not a.eligible:
            evaluations.append(
                CandidateEvaluation(
                    assessment=a,
                    metric_scores=(),
                    group_scores=(),
                    engineering_benefit_score=None,
                    economic_benefit_score=None,
                    final_benefit_score=None,
                    total_benefit_score=None,
                    lifecycle_cost=None,
                    rank=None,
                )
            )
            continue

        m = a.metrics
        assert m is not None

        m_scores = []
        g_scores_dict: dict[ScoringGroup, float] = {g: 0.0 for g in ScoringGroup}
        for metric in ScoringMetric:
            raw = _get_raw(m, metric)
            norm = normalize_metric_benefit(raw, ranges_dict[metric])
            group = _get_metric_group(metric)
            group_weight = _get_group_weight(group, scoring_config)
            subweight = _get_metric_subweight(metric, scoring_config)

            effective_weight = group_weight * subweight
            group_weighted_benefit = norm * subweight
            weighted_benefit = norm * effective_weight

            m_scores.append(
                MetricScore(
                    metric=metric,
                    raw_value=raw,
                    normalized_benefit=norm,
                    weight=effective_weight,
                    weighted_benefit=weighted_benefit,
                )
            )
            g_scores_dict[group] += group_weighted_benefit

        g_scores = []
        for group in ScoringGroup:
            g_score = g_scores_dict[group]
            g_weight = _get_group_weight(group, scoring_config)
            g_scores.append(
                GroupScore(
                    group=group,
                    group_score=g_score,
                    group_weight=g_weight,
                    weighted_score=g_score * g_weight,
                )
            )

        eng_total = math.fsum(gs.weighted_score for gs in g_scores)
        eng_total = max(0.0, min(1.0, eng_total))

        economic_score: float | None = None
        final_score: float | None = None
        l_cost: float | None = None

        if is_cost_aware:
            assert cost_aware_config is not None
            assert min_cost is not None and max_cost is not None
            l_cost = candidate_costs[a.scenario_id]
            if max_cost == min_cost:
                economic_score = 0.0
            else:
                economic_score = (max_cost - l_cost) / (max_cost - min_cost)
                economic_score = max(0.0, min(1.0, economic_score))

            final_score = math.fsum(
                (
                    cost_aware_config.engineering_weight * eng_total,
                    cost_aware_config.lifecycle_cost_weight * economic_score,
                )
            )

        evaluations.append(
            CandidateEvaluation(
                assessment=a,
                metric_scores=tuple(m_scores),
                group_scores=tuple(g_scores),
                engineering_benefit_score=eng_total if is_cost_aware else None,
                economic_benefit_score=economic_score if is_cost_aware else None,
                final_benefit_score=final_score if is_cost_aware else None,
                total_benefit_score=eng_total,
                lifecycle_cost=l_cost,
                rank=None,
            )
        )

    eligible_evals = [e for e in evaluations if e.assessment.eligible]
    ineligible_evals = [e for e in evaluations if not e.assessment.eligible]

    def sort_key(
        e: CandidateEvaluation,
    ) -> tuple[float, float, float, float, float, float, str]:
        assert e.total_benefit_score is not None
        assert e.assessment.metrics is not None

        g_dict = {gs.group: gs.weighted_score for gs in e.group_scores}

        if is_cost_aware:
            assert e.final_benefit_score is not None
            assert e.lifecycle_cost is not None
            return (
                -round(e.final_benefit_score, SCORE_COMPARISON_DECIMALS),
                -round(e.total_benefit_score, SCORE_COMPARISON_DECIMALS),
                round(e.lifecycle_cost, SCORE_COMPARISON_DECIMALS),
                e.assessment.metrics.total_route_length_m,
                e.assessment.metrics.total_active_loss_mw,
                0.0,
                e.assessment.scenario_id,
            )

        if scoring_config.policy_mode == ScoringPolicyMode.LEGACY_COMPATIBILITY:
            return (
                -round(e.total_benefit_score, SCORE_COMPARISON_DECIMALS),
                0.0,
                0.0,
                0.0,
                e.assessment.metrics.total_route_length_m,
                e.assessment.metrics.total_active_loss_mw,
                e.assessment.scenario_id,
            )

        return (
            -round(e.total_benefit_score, SCORE_COMPARISON_DECIMALS),
            -round(g_dict[ScoringGroup.ELECTRICAL], SCORE_COMPARISON_DECIMALS),
            -round(g_dict[ScoringGroup.SPATIAL], SCORE_COMPARISON_DECIMALS),
            -round(g_dict[ScoringGroup.INFRASTRUCTURE], SCORE_COMPARISON_DECIMALS),
            e.assessment.metrics.total_route_length_m,
            e.assessment.metrics.total_active_loss_mw,
            e.assessment.scenario_id,
        )

    eligible_evals.sort(key=sort_key)
    ineligible_evals.sort(key=lambda e: e.assessment.scenario_id)

    engineering_best_sid = None
    if eligible_evals:

        def engineering_key(
            evaluation: CandidateEvaluation,
        ) -> tuple[float, float, float, float, float, float, str]:
            score = evaluation.total_benefit_score
            metrics = evaluation.assessment.metrics
            assert score is not None and metrics is not None
            groups = {
                item.group: item.weighted_score for item in evaluation.group_scores
            }
            return (
                -round(score, SCORE_COMPARISON_DECIMALS),
                -round(groups[ScoringGroup.ELECTRICAL], SCORE_COMPARISON_DECIMALS),
                -round(groups[ScoringGroup.SPATIAL], SCORE_COMPARISON_DECIMALS),
                -round(
                    groups[ScoringGroup.INFRASTRUCTURE],
                    SCORE_COMPARISON_DECIMALS,
                ),
                metrics.total_route_length_m,
                metrics.total_active_loss_mw,
                evaluation.assessment.scenario_id,
            )

        engineering_best_sid = min(
            eligible_evals,
            key=engineering_key,
        ).assessment.scenario_id
        if is_cost_aware:
            lowest_cost_sid = min(
                eligible_evals,
                key=lambda evaluation: (
                    evaluation.lifecycle_cost
                    if evaluation.lifecycle_cost is not None
                    else math.inf,
                    evaluation.assessment.scenario_id,
                ),
            ).assessment.scenario_id

    ranked_evals = [
        replace(evaluation, rank=rank)
        for rank, evaluation in enumerate(eligible_evals, start=1)
    ]
    ranked_evals.extend(ineligible_evals)

    policy_name = scoring_config.policy_mode.value
    if is_cost_aware:
        assert cost_aware_config is not None
        engineering_percent = int(cost_aware_config.engineering_weight * 100)
        lifecycle_percent = int(cost_aware_config.lifecycle_cost_weight * 100)
        policy_name = f"COST_AWARE_ENG_{engineering_percent}_ECO_{lifecycle_percent}"

    if not eligible_evals:
        return OptimizationRecommendation(
            status=OptimizationRecommendationStatus.NO_FEASIBLE_CANDIDATE,
            recommended_scenario_id=None,
            engineering_best_scenario_id=None,
            lowest_cost_scenario_id=None,
            policy=policy_name,
            economic_context_id=economic_context_id,
            evaluations=tuple(ranked_evals),
            normalization_ranges=ranges_tuple,
            reasons=(),
            baseline_comparison_status="baseline_unavailable",
            baseline_comparisons=(),
        )

    winner = ranked_evals[0]
    winner_id = winner.assessment.scenario_id

    reasons: list[RecommendationReason] = []
    if len(eligible_evals) == 1:
        reasons.append(
            RecommendationReason(
                code=RecommendationReasonCode.ONLY_ELIGIBLE_CANDIDATE,
                message=("Only one candidate satisfied all eligibility checks"),
            )
        )
    else:
        if is_cost_aware:
            assert winner.final_benefit_score is not None
            reasons.append(
                RecommendationReason(
                    code=RecommendationReasonCode.HIGHEST_COST_AWARE_BENEFIT,
                    message=(
                        f"Achieved the highest cost-aware benefit score "
                        f"({winner.final_benefit_score:.3f})"
                    ),
                    candidate_value=winner.final_benefit_score,
                )
            )
            if winner_id == lowest_cost_sid:
                reasons.append(
                    RecommendationReason(
                        code=RecommendationReasonCode.LOWEST_LIFECYCLE_COST,
                        message="Has the lowest lifecycle cost among feasible options",
                        candidate_value=winner.lifecycle_cost,
                    )
                )
            if winner_id == engineering_best_sid:
                reasons.append(
                    RecommendationReason(
                        code=RecommendationReasonCode.HIGHEST_ENGINEERING_BENEFIT,
                        message=(
                            "Has the highest engineering benefit among feasible options"
                        ),
                        candidate_value=winner.engineering_benefit_score,
                    )
                )
            if winner_id != lowest_cost_sid and winner_id != engineering_best_sid:
                reasons.append(
                    RecommendationReason(
                        code=RecommendationReasonCode.BALANCED_ENGINEERING_AND_COST,
                        message=(
                            "Provides the best balanced trade-off between engineering "
                            "and economics"
                        ),
                        candidate_value=winner.final_benefit_score,
                    )
                )
        else:
            assert winner.total_benefit_score is not None
            reasons.append(
                RecommendationReason(
                    code=RecommendationReasonCode.HIGHEST_TOTAL_BENEFIT,
                    message=(
                        "Achieved the highest total benefit score "
                        f"({winner.total_benefit_score:.3f})"
                    ),
                    candidate_value=winner.total_benefit_score,
                )
            )

        winner_metrics = winner.assessment.metrics
        assert winner_metrics is not None

        def _is_best(m: ScoringMetric) -> bool:
            norm_range = ranges_dict[m]
            if norm_range.constant:
                return False
            assert winner_metrics is not None
            val = _get_raw(winner_metrics, m)
            if m == ScoringMetric.VOLTAGE_MARGIN:
                return round(val, SCORE_COMPARISON_DECIMALS) == round(
                    norm_range.maximum, SCORE_COMPARISON_DECIMALS
                )
            return round(val, SCORE_COMPARISON_DECIMALS) == round(
                norm_range.minimum, SCORE_COMPARISON_DECIMALS
            )

        if _is_best(ScoringMetric.TRAVERSAL_COST):
            reasons.append(
                RecommendationReason(
                    code=RecommendationReasonCode.HIGHEST_SPATIAL_SCORE,
                    message=(
                        "Achieved the highest spatial benefit "
                        "(e.g. lowest traversal cost)"
                    ),
                )
            )
        if _is_best(ScoringMetric.SOFT_CONSTRAINT_OVERLAP_LENGTH):
            reasons.append(
                RecommendationReason(
                    code=RecommendationReasonCode.LOWEST_SOFT_CONSTRAINT_OVERLAP,
                    message="Has the lowest soft-constraint overlap",
                    metric=ScoringMetric.SOFT_CONSTRAINT_OVERLAP_LENGTH,
                    candidate_value=winner_metrics.soft_constraint_overlap_length_m,
                )
            )
        if _is_best(ScoringMetric.PHYSICAL_POLE_COUNT):
            reasons.append(
                RecommendationReason(
                    code=RecommendationReasonCode.HIGHEST_INFRASTRUCTURE_SCORE,
                    message=(
                        "Achieved the highest infrastructure benefit "
                        "(e.g. lowest pole count)"
                    ),
                )
            )
        if _is_best(ScoringMetric.ACTIVE_LOSS):
            reasons.append(
                RecommendationReason(
                    code=RecommendationReasonCode.HIGHEST_ELECTRICAL_SCORE,
                    message=(
                        "Achieved the highest electrical benefit "
                        "(e.g. lowest active losses)"
                    ),
                )
            )

    baseline_ids = sorted(
        wrapper.electrical.scenario.scenario_id
        for wrapper in wrappers
        if wrapper.electrical.scenario.strategy == ScenarioStrategy.BASELINE
    )
    comp_status = "baseline_unavailable"
    comp_list: list[MetricComparison] = []

    if baseline_ids:
        baseline_eval = next(
            evaluation
            for evaluation in evaluations
            if evaluation.assessment.scenario_id == baseline_ids[0]
        )
        if (
            not baseline_eval.assessment.eligible
            or not baseline_eval.assessment.metrics
        ):
            comp_status = "baseline_not_comparable"
        else:
            comp_status = "baseline_comparable"
            b_metrics = baseline_eval.assessment.metrics
            w_metrics = winner.assessment.metrics
            assert w_metrics is not None

            for sm in ScoringMetric:
                b_val = _get_raw(b_metrics, sm)
                w_val = _get_raw(w_metrics, sm)
                diff = w_val - b_val
                comp_list.append(
                    MetricComparison(
                        metric=sm,
                        baseline_value=b_val,
                        recommended_value=w_val,
                        absolute_delta=diff,
                        relative_delta_percent=(
                            diff / b_val * 100.0
                            if not math.isclose(b_val, 0.0, abs_tol=1e-9)
                            else None
                        ),
                        preferred_direction="lower"
                        if sm != ScoringMetric.VOLTAGE_MARGIN
                        else "higher",
                    )
                )

            winner_score = (
                winner.final_benefit_score
                if is_cost_aware
                else winner.total_benefit_score
            )
            baseline_score = (
                baseline_eval.final_benefit_score
                if is_cost_aware
                else baseline_eval.total_benefit_score
            )
            if (
                winner_id != baseline_eval.assessment.scenario_id
                and winner_score is not None
                and baseline_score is not None
                and winner_score > baseline_score
            ):
                reasons.append(
                    RecommendationReason(
                        code=RecommendationReasonCode.BASELINE_IMPROVEMENT,
                        message=(
                            f"Outperforms baseline ({baseline_ids[0]}) in "
                            "multi-objective evaluation"
                        ),
                    )
                )

            if is_cost_aware:
                b_ca = complete_cost_assessments.get(
                    baseline_eval.assessment.scenario_id
                )
                w_ca = complete_cost_assessments.get(winner_id)

                if b_ca and b_ca.cost and w_ca and w_ca.cost:
                    b_capex = float(b_ca.cost.total_capex)
                    w_capex = float(w_ca.cost.total_capex)
                    diff_capex = w_capex - b_capex
                    comp_list.append(
                        MetricComparison(
                            metric="total_capex",
                            baseline_value=b_capex,
                            recommended_value=w_capex,
                            absolute_delta=diff_capex,
                            relative_delta_percent=None,
                            preferred_direction="lower",
                        )
                    )

                    b_opex = float(b_ca.cost.present_value_opex)
                    w_opex = float(w_ca.cost.present_value_opex)
                    diff_opex = w_opex - b_opex
                    comp_list.append(
                        MetricComparison(
                            metric="present_value_opex",
                            baseline_value=b_opex,
                            recommended_value=w_opex,
                            absolute_delta=diff_opex,
                            relative_delta_percent=None,
                            preferred_direction="lower",
                        )
                    )

                    b_lc = float(b_ca.cost.lifecycle_cost)
                    w_lc = float(w_ca.cost.lifecycle_cost)
                    diff_lc = w_lc - b_lc
                    comp_list.append(
                        MetricComparison(
                            metric="lifecycle_cost",
                            baseline_value=b_lc,
                            recommended_value=w_lc,
                            absolute_delta=diff_lc,
                            relative_delta_percent=None,
                            preferred_direction="lower",
                        )
                    )

    return OptimizationRecommendation(
        status=OptimizationRecommendationStatus.SUCCESS,
        recommended_scenario_id=winner_id,
        engineering_best_scenario_id=engineering_best_sid,
        lowest_cost_scenario_id=lowest_cost_sid,
        policy=policy_name,
        economic_context_id=economic_context_id,
        evaluations=tuple(ranked_evals),
        normalization_ranges=ranges_tuple,
        reasons=tuple(reasons),
        baseline_comparison_status=comp_status,
        baseline_comparisons=tuple(comp_list),
    )
