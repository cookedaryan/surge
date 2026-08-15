import re
import sys
from pathlib import Path

path = Path("tests/test_optimisation_scoring.py")
content = path.read_text(encoding="utf-8")

# 1. Update imports
content = re.sub(
    r"from app\.optimisation\.scoring_models import \(.*?\)",
    """from app.optimisation.scoring_models import (
    CandidateScoringConfig,
    DisqualificationCode,
    ElectricallyEvaluatedScenario,
    EngineeringEvaluatedScenario,
    CandidateEngineeringAssessment,
    CandidateEngineeringMetrics,
    ElectricalScoringWeights,
    ScoringPolicyMode,
    SpatialScoringWeights,
    OptimizationRecommendationStatus,
    RecommendationReasonCode,
    ScoringMetric,
)""",
    content,
    flags=re.DOTALL
)

# 2. Update base_scoring_config
content = re.sub(
    r"def base_scoring_config.*?return CandidateScoringConfig\([^)]+\)",
    """def base_scoring_config() -> CandidateScoringConfig:
    return CandidateScoringConfig(
        policy_mode=ScoringPolicyMode.LEGACY_COMPATIBILITY,
        physical_weight=0.4,
        spatial_weight=0.0,
        infrastructure_weight=0.0,
        electrical_weight=0.6,
        spatial_subweights=SpatialScoringWeights(0.0, 0.0, 0.0, 0.0),
        electrical_subweights=ElectricalScoringWeights(
            active_loss=0.25 / 0.6,
            cable_loading=0.2 / 0.6,
            voltage_margin=0.15 / 0.6,
        )
    )""",
    content,
    flags=re.DOTALL
)

# 3. Update manual calculation config
content = re.sub(
    r"config = CandidateScoringConfig\(0\.4, 0\.3, 0\.2, 0\.1\)",
    """config = CandidateScoringConfig(
        policy_mode=ScoringPolicyMode.LEGACY_COMPATIBILITY,
        physical_weight=0.4,
        spatial_weight=0.0,
        infrastructure_weight=0.0,
        electrical_weight=0.6,
        spatial_subweights=SpatialScoringWeights(0.0, 0.0, 0.0, 0.0),
        electrical_subweights=ElectricalScoringWeights(
            active_loss=0.3 / 0.6,
            cable_loading=0.2 / 0.6,
            voltage_margin=0.1 / 0.6,
        )
    )""",
    content,
)

# 4. Update make_wrapper
new_make_wrapper = """def make_wrapper(
    scenario: PNCScenario,
    result: LoadFlowNetworkResult,
    electrical_context_id: str = "EC-1",
) -> EngineeringEvaluatedScenario:
    metrics = None
    if result.is_valid and result.converged:
        v_margin = 0.0
        if result.minimum_voltage_pu is not None and result.maximum_voltage_pu is not None:
            v_margin = min(
                result.minimum_voltage_pu - 0.95,
                1.05 - result.maximum_voltage_pu
            )
        metrics = CandidateEngineeringMetrics(
            total_route_length_m=scenario.total_route_length_m,
            total_traversal_cost=scenario.total_route_length_m,
            affected_parcel_count=10,
            road_crossing_count=2,
            soft_constraint_overlap_length_m=0.0,
            physical_pole_count=20,
            total_active_loss_mw=result.total_active_loss_mw or 0.0,
            maximum_loading_percent=result.maximum_loading_percent or 0.0,
            voltage_margin_pu=v_margin,
            environmental_overlap_m2=0.0,
        )
        
    assessment = CandidateEngineeringAssessment(
        scenario_id=scenario.scenario_id,
        engineering_metrics_available=True if metrics else False,
        extraction_failures=(),
        hard_violation_ids=(),
        metrics=metrics,
        pole_result=None,
    )
    
    return EngineeringEvaluatedScenario(
        electrical=ElectricallyEvaluatedScenario(
            scenario=scenario,
            load_flow_result=result,
            electrical_context_id=electrical_context_id,
        ),
        engineering_assessment=assessment,
    )"""

content = re.sub(
    r"def make_wrapper\(.*?\) -> ElectricallyEvaluatedScenario:.*?return ElectricallyEvaluatedScenario\([^)]+\)",
    new_make_wrapper,
    content,
    flags=re.DOTALL
)

# 5. Remove base_load_flow_config from evaluate_cohort
content = re.sub(
    r"evaluate_cohort\((.*?),\s*base_scoring_config,\s*base_load_flow_config\)",
    r"evaluate_cohort(\1, base_scoring_config)",
    content,
)

# 6. Some places use `config, base_load_flow_config`
content = re.sub(
    r"evaluate_cohort\((.*?),\s*config,\s*base_load_flow_config\)",
    r"evaluate_cohort(\1, config)",
    content,
)

path.write_text(content, encoding="utf-8")
print("Done rewriting tests/test_optimisation_scoring.py")
