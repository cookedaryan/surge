"""Multi-objective scoring and recommendation pipeline."""

import math
from typing import Literal

from app.electrical.load_flow.config import LoadFlowConfig
from app.optimisation.engineering_metrics import calculate_voltage_margin
from app.optimisation.scenario_models import ScenarioStrategy
from app.optimisation.scoring_models import (
    CandidateAssessment,
    CandidateEvaluation,
    CandidateMetrics,
    CandidateScoringConfig,
    Disqualification,
    DisqualificationCode,
    ElectricallyEvaluatedScenario,
    MetricComparison,
    MetricScore,
    NormalizationRange,
    OptimizationRecommendation,
    OptimizationRecommendationStatus,
    RecommendationReason,
    RecommendationReasonCode,
    ScoringMetric,
)


def _format_relative_delta(val: float | None) -> str:
    if val is None:
        return "N/A"
    if val > 0:
        return f"+{val:.1f}%"
    return f"{val:.1f}%"


def _format_absolute_delta(val: float) -> str:
    if val > 0:
        return f"+{val:.3g}"
    return f"{val:.3g}"


def extract_candidate_assessment(
    wrapper: ElectricallyEvaluatedScenario,
    load_flow_config: LoadFlowConfig,
) -> CandidateAssessment:
    """Extract metrics and determine basic eligibility for a single candidate."""
    scenario_id = wrapper.scenario.scenario_id
    res = wrapper.load_flow_result

    if not res.converged:
        return CandidateAssessment(
            scenario_id=scenario_id,
            eligible=False,
            disqualifications=(
                Disqualification(
                    code=DisqualificationCode.LOAD_FLOW_NOT_CONVERGED,
                    message="Load flow did not converge",
                ),
            ),
            metrics=None,
        )

    disqualifications: list[Disqualification] = []

    # Reconcile result shape against the candidate network
    n = wrapper.scenario.network
    bus_count = len(res.buses)
    seg_count = len(res.segments)
    fdr_count = len(res.feeders)
    # The load flow model contains WTGs + 1 substation bus.
    expected_buses = n.wtg_count + 1
    if (
        bus_count != expected_buses
        or seg_count != n.segment_count
        or fdr_count != n.feeder_count
    ):
        disqualifications.append(
            Disqualification(
                code=DisqualificationCode.TOPOLOGY_MISMATCH,
                message=(
                    f"Result shape (buses={bus_count}, segments={seg_count}, "
                    f"feeders={fdr_count}) does not match network "
                    f"(wtgs+1={expected_buses}, segments={n.segment_count}, "
                    f"feeders={n.feeder_count})"
                ),
            )
        )

    # Collect all electrical violations mapped as disqualifications
    if not res.is_valid or len(res.violations) > 0:
        underlying_codes = tuple(sorted({v.code for v in res.violations}))
        disqualifications.append(
            Disqualification(
                code=DisqualificationCode.ELECTRICAL_VIOLATION,
                message="Candidate contains electrical violations or is marked invalid",
                underlying_violations=underlying_codes,
            )
        )

    # Check for missing metrics
    required_metrics = [
        wrapper.scenario.network.total_route_length_m,
        res.total_active_loss_mw,
        res.maximum_loading_percent,
        res.minimum_voltage_pu,
        res.maximum_voltage_pu,
    ]
    if any(val is None for val in required_metrics):
        disqualifications.append(
            Disqualification(
                code=DisqualificationCode.ELECTRICAL_METRICS_MISSING,
                message="Required load flow metrics are missing",
            )
        )
    elif any(not math.isfinite(val) for val in required_metrics):  # type: ignore
        disqualifications.append(
            Disqualification(
                code=DisqualificationCode.RESULT_NOT_FINITE,
                message="Required load flow metrics are not finite",
            )
        )

    if disqualifications:
        return CandidateAssessment(
            scenario_id=scenario_id,
            eligible=False,
            disqualifications=tuple(disqualifications),
            metrics=None,
        )

    min_v = res.minimum_voltage_pu
    max_v = res.maximum_voltage_pu
    assert min_v is not None and max_v is not None

    voltage_margin_pu = calculate_voltage_margin(
        min_v,
        max_v,
        load_flow_config.min_voltage_pu,
        load_flow_config.max_voltage_pu,
    )

    # total_route_length_m is guaranteed finite from PY-017
    # others are guaranteed non-None and finite by the checks above
    metrics = CandidateMetrics(
        total_route_length_m=wrapper.scenario.network.total_route_length_m,
        total_active_loss_mw=res.total_active_loss_mw,  # type: ignore
        maximum_loading_percent=res.maximum_loading_percent,  # type: ignore
        voltage_margin_pu=voltage_margin_pu,
    )

    return CandidateAssessment(
        scenario_id=scenario_id,
        eligible=True,
        disqualifications=(),
        metrics=metrics,
    )


def compute_normalization_ranges(
    eligible_assessments: list[CandidateAssessment],
) -> tuple[NormalizationRange, ...]:
    """Compute min/max bounds for all scoring metrics across the eligible cohort."""
    if not eligible_assessments:
        return ()

    def extract_val(metrics: CandidateMetrics, metric: ScoringMetric) -> float:
        if metric == ScoringMetric.ROUTE_LENGTH:
            return metrics.total_route_length_m
        if metric == ScoringMetric.ACTIVE_LOSS:
            return metrics.total_active_loss_mw
        if metric == ScoringMetric.CABLE_LOADING:
            return metrics.maximum_loading_percent
        if metric == ScoringMetric.VOLTAGE_MARGIN:
            return metrics.voltage_margin_pu
        raise ValueError(f"Unknown metric {metric}")

    ranges = []
    for metric in ScoringMetric:
        vals = [
            extract_val(a.metrics, metric)  # type: ignore
            for a in eligible_assessments
        ]
        min_v = min(vals)
        max_v = max(vals)
        ranges.append(
            NormalizationRange(
                metric=metric,
                minimum=min_v,
                maximum=max_v,
                constant=min_v == max_v,
            )
        )
    return tuple(ranges)


def normalize_metric_benefit(
    raw_value: float,
    norm_range: NormalizationRange,
) -> float:
    """Normalize such that 1.0 is the best benefit and 0.0 is the worst."""
    if norm_range.constant:
        return 0.0

    if norm_range.metric in (
        ScoringMetric.ROUTE_LENGTH,
        ScoringMetric.ACTIVE_LOSS,
        ScoringMetric.CABLE_LOADING,
    ):
        # Lower is better
        norm = (norm_range.maximum - raw_value) / (
            norm_range.maximum - norm_range.minimum
        )
    elif norm_range.metric == ScoringMetric.VOLTAGE_MARGIN:
        # Higher is better
        norm = (raw_value - norm_range.minimum) / (
            norm_range.maximum - norm_range.minimum
        )
    else:
        raise ValueError(f"Unknown metric {norm_range.metric}")

    return max(0.0, min(1.0, norm))


def evaluate_cohort(
    wrappers: tuple[ElectricallyEvaluatedScenario, ...],
    scoring_config: CandidateScoringConfig,
    load_flow_config: LoadFlowConfig,
) -> OptimizationRecommendation:
    """Evaluate, score, and rank a set of electrically evaluated PNC scenarios."""
    if not wrappers:
        raise ValueError("Must provide at least one candidate for scoring")

    comp_group_id = wrappers[0].scenario.comparison_group_id
    elec_context_id = wrappers[0].electrical_context_id
    seen_ids = set()
    seen_fps = set()

    for w in wrappers:
        if w.scenario.comparison_group_id != comp_group_id:
            raise ValueError("All candidates must share the same comparison_group_id")
        if w.electrical_context_id != elec_context_id:
            raise ValueError("All candidates must share the same electrical_context_id")

        sid = w.scenario.scenario_id
        if sid in seen_ids:
            raise ValueError(f"Duplicate scenario_id: {sid}")
        seen_ids.add(sid)

        fp = w.scenario.topology_fingerprint
        if fp in seen_fps:
            raise ValueError(f"Duplicate topology_fingerprint: {fp}")
        seen_fps.add(fp)

    # 1. Eligibility Extraction
    assessments = [extract_candidate_assessment(w, load_flow_config) for w in wrappers]
    eligible_assessments = [a for a in assessments if a.eligible]

    # 2. Normalization Bounds
    ranges_tuple = compute_normalization_ranges(eligible_assessments)
    ranges_dict = {r.metric: r for r in ranges_tuple}

    # 3. Scoring
    evaluations: list[CandidateEvaluation] = []

    def get_weight(metric: ScoringMetric) -> float:
        if metric == ScoringMetric.ROUTE_LENGTH:
            return scoring_config.route_length_weight
        if metric == ScoringMetric.ACTIVE_LOSS:
            return scoring_config.electrical_loss_weight
        if metric == ScoringMetric.CABLE_LOADING:
            return scoring_config.cable_loading_weight
        if metric == ScoringMetric.VOLTAGE_MARGIN:
            return scoring_config.voltage_margin_weight
        raise ValueError(f"Unknown metric {metric}")

    def get_raw(m: CandidateMetrics, metric: ScoringMetric) -> float:
        if metric == ScoringMetric.ROUTE_LENGTH:
            return m.total_route_length_m
        if metric == ScoringMetric.ACTIVE_LOSS:
            return m.total_active_loss_mw
        if metric == ScoringMetric.CABLE_LOADING:
            return m.maximum_loading_percent
        if metric == ScoringMetric.VOLTAGE_MARGIN:
            return m.voltage_margin_pu
        raise ValueError(f"Unknown metric {metric}")

    for a in assessments:
        if not a.eligible:
            evaluations.append(
                CandidateEvaluation(
                    assessment=a,
                    metric_scores=(),
                    total_benefit_score=None,
                    rank=None,
                )
            )
            continue

        m = a.metrics
        assert m is not None

        m_scores = []
        for metric in ScoringMetric:
            raw = get_raw(m, metric)
            norm = normalize_metric_benefit(raw, ranges_dict[metric])
            weight = get_weight(metric)
            m_scores.append(
                MetricScore(
                    metric=metric,
                    raw_value=raw,
                    normalized_benefit=norm,
                    weight=weight,
                    weighted_benefit=norm * weight,
                )
            )

        total = math.fsum(ms.weighted_benefit for ms in m_scores)
        total = max(0.0, min(1.0, total))

        evaluations.append(
            CandidateEvaluation(
                assessment=a,
                metric_scores=tuple(m_scores),
                total_benefit_score=total,
                rank=None,
            )
        )

    # 4. Ranking
    eligible_evals = [e for e in evaluations if e.assessment.eligible]
    ineligible_evals = [e for e in evaluations if not e.assessment.eligible]

    def sort_key(e: CandidateEvaluation) -> tuple[float, float, float, str]:
        assert e.total_benefit_score is not None
        assert e.assessment.metrics is not None
        # Rank by total score desc, route length asc, loss asc, scenario id asc
        return (
            -e.total_benefit_score,
            e.assessment.metrics.total_route_length_m,
            e.assessment.metrics.total_active_loss_mw,
            e.assessment.scenario_id,
        )

    eligible_evals.sort(key=sort_key)
    ineligible_evals.sort(key=lambda e: e.assessment.scenario_id)

    ranked_evals = []
    for rank, e in enumerate(eligible_evals, start=1):
        ranked_evals.append(
            CandidateEvaluation(
                assessment=e.assessment,
                metric_scores=e.metric_scores,
                total_benefit_score=e.total_benefit_score,
                rank=rank,
            )
        )
    ranked_evals.extend(ineligible_evals)

    # 5. Recommendation & Explainability
    if not eligible_evals:
        return OptimizationRecommendation(
            status=OptimizationRecommendationStatus.NO_FEASIBLE_CANDIDATE,
            recommended_scenario_id=None,
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
                message="Only one candidate was electrically feasible",
            )
        )
    else:
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

        # Check if winner has the absolute best raw value in the cohort for any metric
        if (
            not ranges_dict[ScoringMetric.ROUTE_LENGTH].constant
            and scoring_config.route_length_weight > 0.0
            and math.isclose(
                winner_metrics.total_route_length_m,
                ranges_dict[ScoringMetric.ROUTE_LENGTH].minimum,
            )
        ):
            reasons.append(
                RecommendationReason(
                    code=RecommendationReasonCode.SHORTEST_ROUTE,
                    message="Has the shortest routed length",
                    metric=ScoringMetric.ROUTE_LENGTH,
                    candidate_value=winner_metrics.total_route_length_m,
                )
            )
        if (
            not ranges_dict[ScoringMetric.ACTIVE_LOSS].constant
            and scoring_config.electrical_loss_weight > 0.0
            and math.isclose(
                winner_metrics.total_active_loss_mw,
                ranges_dict[ScoringMetric.ACTIVE_LOSS].minimum,
            )
        ):
            reasons.append(
                RecommendationReason(
                    code=RecommendationReasonCode.LOWEST_ACTIVE_LOSS,
                    message="Has the lowest total active loss",
                    metric=ScoringMetric.ACTIVE_LOSS,
                    candidate_value=winner_metrics.total_active_loss_mw,
                )
            )
        if (
            not ranges_dict[ScoringMetric.CABLE_LOADING].constant
            and scoring_config.cable_loading_weight > 0.0
            and math.isclose(
                winner_metrics.maximum_loading_percent,
                ranges_dict[ScoringMetric.CABLE_LOADING].minimum,
            )
        ):
            reasons.append(
                RecommendationReason(
                    code=RecommendationReasonCode.LOWEST_CABLE_LOADING,
                    message="Has the lowest maximum cable loading",
                    metric=ScoringMetric.CABLE_LOADING,
                    candidate_value=winner_metrics.maximum_loading_percent,
                )
            )
        if (
            not ranges_dict[ScoringMetric.VOLTAGE_MARGIN].constant
            and scoring_config.voltage_margin_weight > 0.0
            and math.isclose(
                winner_metrics.voltage_margin_pu,
                ranges_dict[ScoringMetric.VOLTAGE_MARGIN].maximum,
            )
        ):
            reasons.append(
                RecommendationReason(
                    code=RecommendationReasonCode.BEST_VOLTAGE_MARGIN,
                    message="Has the best voltage operating margin",
                    metric=ScoringMetric.VOLTAGE_MARGIN,
                    candidate_value=winner_metrics.voltage_margin_pu,
                )
            )

    # Find Baseline
    baseline_wrappers = [
        w
        for w in wrappers
        if w.scenario.parameters.strategy == ScenarioStrategy.BASELINE
    ]

    if not baseline_wrappers:
        baseline_wrapper = None
    elif len(baseline_wrappers) == 1:
        baseline_wrapper = baseline_wrappers[0]
    else:
        # Deterministically select one baseline if multiple exist
        baseline_wrapper = sorted(
            baseline_wrappers, key=lambda w: w.scenario.scenario_id
        )[0]

    baseline_status = "baseline_comparable"
    baseline_comps: list[MetricComparison] = []

    if baseline_wrapper is None:
        baseline_status = "baseline_unavailable"
    else:
        baseline_eval = next(
            (
                e
                for e in ranked_evals
                if e.assessment.scenario_id == baseline_wrapper.scenario.scenario_id
            ),
            None,
        )
        assert baseline_eval is not None

        if (
            not baseline_eval.assessment.eligible
            or baseline_eval.assessment.metrics is None
        ):
            baseline_status = "baseline_not_comparable"
        else:
            w_metrics = winner.assessment.metrics
            b_metrics = baseline_eval.assessment.metrics
            assert w_metrics is not None and b_metrics is not None

            def make_comp(
                metric: ScoringMetric,
                w_val: float,
                b_val: float,
                direction: Literal["higher", "lower"],
            ) -> MetricComparison:
                abs_delta = w_val - b_val
                rel_delta = (
                    (abs_delta / b_val * 100.0)
                    if not math.isclose(b_val, 0.0, abs_tol=1e-9)
                    else None
                )
                return MetricComparison(
                    metric=metric,
                    recommended_value=w_val,
                    baseline_value=b_val,
                    absolute_delta=abs_delta,
                    relative_delta_percent=rel_delta,
                    preferred_direction=direction,
                )

            baseline_comps.extend(
                [
                    make_comp(
                        ScoringMetric.ROUTE_LENGTH,
                        w_metrics.total_route_length_m,
                        b_metrics.total_route_length_m,
                        "lower",
                    ),
                    make_comp(
                        ScoringMetric.ACTIVE_LOSS,
                        w_metrics.total_active_loss_mw,
                        b_metrics.total_active_loss_mw,
                        "lower",
                    ),
                    make_comp(
                        ScoringMetric.CABLE_LOADING,
                        w_metrics.maximum_loading_percent,
                        b_metrics.maximum_loading_percent,
                        "lower",
                    ),
                    make_comp(
                        ScoringMetric.VOLTAGE_MARGIN,
                        w_metrics.voltage_margin_pu,
                        b_metrics.voltage_margin_pu,
                        "higher",
                    ),
                ]
            )

            if winner_id != baseline_wrapper.scenario.scenario_id:
                # Only emit if there is a real multi-objective score advantage
                w_score = winner.total_benefit_score
                b_score = baseline_eval.total_benefit_score
                if w_score is not None and b_score is not None and w_score > b_score:
                    reasons.append(
                        RecommendationReason(
                            code=RecommendationReasonCode.BASELINE_IMPROVEMENT,
                            message=(
                                "Outperforms baseline "
                                f"({baseline_wrapper.scenario.scenario_id}) "
                                "in multi-objective evaluation"
                            ),
                        )
                    )

    return OptimizationRecommendation(
        status=OptimizationRecommendationStatus.SUCCESS,
        recommended_scenario_id=winner_id,
        evaluations=tuple(ranked_evals),
        normalization_ranges=ranges_tuple,
        reasons=tuple(reasons),
        baseline_comparison_status=baseline_status,
        baseline_comparisons=tuple(baseline_comps),
    )
