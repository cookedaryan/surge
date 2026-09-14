"""Read-only audit probes. Run from the audited optimisation-python directory."""
import hashlib
import importlib.metadata
import json
from dataclasses import replace
from pathlib import Path
import random
import sys

sys.path.insert(0, str(Path.cwd()))
import networkx as nx
from pyproj import CRS
from shapely.geometry import Point
from app.algorithms.pole_placement import PolePlacementConfig
from app.algorithms.route_graph import build_project_graph
from app.algorithms.wtg_grouping import GroupingObjective, group_wtgs
from app.electrical.load_flow.config import LoadFlowCableType, LoadFlowConfig
from app.electrical.load_flow.models import WTGOperatingPoint
from app.gis.cost_surface import build_project_cost_surface
from app.models.spatial import ProjectSpatialData, Substation, WindTurbine
from app.optimisation.orchestrator import optimise_project
from app.optimisation.scenario_models import ScenarioGenerationConfig
from app.optimisation.scenarios import _apply_long_edge_penalty, generate_pnc_scenarios
from app.optimisation.search_cache import CandidateEvaluationCache
from app.optimisation.search_models import CandidateSearchConfig
from app.optimisation.workflow_models import ProjectInput
from app.schemas.v2.domain_mapping import to_workflow_invocation, to_api_response
from app.schemas.v2.optimise import OptimiseProjectRequest, PoleConfigRequest
from tests.test_optimisation_orchestrator import base_config, project_input

result = {}
locked = {}
for line in Path('requirements.lock.txt').read_text().splitlines():
    if '==' in line:
        name, version = line.split('==', 1)
        try:
            actual = importlib.metadata.version(name)
        except importlib.metadata.PackageNotFoundError:
            actual = 'MISSING'
        if actual != version:
            locked[name] = {'locked': version, 'actual': actual}
result['dependency_pin_mismatches'] = locked
result['api_controls'] = {
    'search_request_field': 'search' in OptimiseProjectRequest.model_fields,
    'micro_siting_request_field': 'micro_siting' in PoleConfigRequest.model_fields,
}
unchanged = 0
for seed in range(100):
    rng = random.Random(seed)
    graph = nx.complete_graph(8)
    for _, _, data in graph.edges(data=True):
        data['weight'] = rng.uniform(0.01, 1000)
    before = {tuple(sorted(e)) for e in nx.minimum_spanning_tree(graph).edges()}
    after = {tuple(sorted(e)) for e in nx.minimum_spanning_tree(_apply_long_edge_penalty(graph, 2.0)).edges()}
    unchanged += before == after
result['long_edge_penalty'] = {'graphs': 100, 'unchanged_msts': unchanged}

inp = project_input.__wrapped__()
cfg = base_config.__wrapped__()
generation = generate_pnc_scenarios(inp.project_data, inp.feeder_capacity_mw, inp.cost_surface, ScenarioGenerationConfig(candidate_count=5, project_id=inp.project_id))
result['five_scheduled_seeds'] = {
    'accepted': len(generation.candidates),
    'attempts': [{'parameter': a.parameter_set_id, 'outcome': a.outcome.value} for a in generation.attempts],
}
balanced_42 = group_wtgs(inp.project_data, inp.feeder_capacity_mw, random_state=42, objective=GroupingObjective.BALANCE_WTG_COUNT)
balanced_17 = group_wtgs(inp.project_data, inp.feeder_capacity_mw, random_state=17, objective=GroupingObjective.BALANCE_WTG_COUNT)
result['balanced_seed_change_equal_memberships'] = [a.turbine_ids for a in balanced_42.assignments] == [a.turbine_ids for a in balanced_17.assignments]
search_cfg = replace(cfg, search=CandidateSearchConfig(enabled=True, max_rounds=1, beam_width=1, max_neighbors_per_parent=1))
cache = CandidateEvaluationCache()
first = optimise_project(inp, search_cfg, evaluation_cache=cache)
second = optimise_project(inp, search_cfg, evaluation_cache=cache)
result['cache_land_round_trip'] = {
    'first': [{'scenario': c.scenario.scenario_id, 'land_present': c.land_assessment is not None} for c in first.candidates if c.scenario.lineage],
    'second': [{'scenario': c.scenario.scenario_id, 'land_present': c.land_assessment is not None} for c in second.candidates if c.scenario.lineage],
    'cache_hits': second.search_result.statistics.evaluation_cache_hit_count,
}
result['real_fixture_runs'] = []
for name in ('mvp_demo_project_v2.json', 'constraint_demo_project_v2.json'):
    request = OptimiseProjectRequest.model_validate_json((Path('tests/fixtures') / name).read_text())
    invocation = to_workflow_invocation(request)
    workflow = optimise_project(invocation.project_input, invocation.config)
    winner_id = workflow.recommendation.recommended_scenario_id if workflow.recommendation else None
    winner = next((c for c in workflow.candidates if c.scenario.scenario_id == winner_id), None)
    result['real_fixture_runs'].append({
        'fixture': name, 'status': workflow.status.value, 'candidates': len(workflow.candidates),
        'winner': winner_id, 'search_enabled': invocation.config.search.enabled,
        'route_length_m': winner.scenario.total_route_length_m if winner else None,
        'active_loss_mw': winner.load_flow_result.total_active_loss_mw if winner else None,
        'physical_poles': len(workflow.pole_network.physical_poles) if workflow.pole_network else None,
    })

# Real Pandapower repair, without mocking the solver or sizing.
crs = CRS.from_epsg(32644)
spatial = ProjectSpatialData(turbines=(WindTurbine(turbine_id='T1', location=Point(520000, 800000), capacity_mw=5.0),), substation=Substation(substation_id='SS', location=Point(500000, 800000)), projected_crs=crs)
electrical = LoadFlowConfig(nominal_voltage_kv=33.0, slack_voltage_pu=1.0, min_voltage_pu=0.95, max_voltage_pu=1.01, system_base_mva=100.0, cable_types=(LoadFlowCableType(cable_type_id='SMALL', resistance_ohm_per_km=1.0, reactance_ohm_per_km=0.1, capacitance_nf_per_km=0.0, max_current_a=100.0), LoadFlowCableType(cable_type_id='LARGE', resistance_ohm_per_km=0.05, reactance_ohm_per_km=0.05, capacitance_nf_per_km=0.0, max_current_a=400.0)), default_cable_type_id='SMALL', segment_cable_type_ids={})
repair_input = ProjectInput(project_id='AUDIT-REAL-REPAIR', project_data=spatial, cost_surface=build_project_cost_surface(spatial, resolution_m=100), feeder_capacity_mw=6.0, operating_points=(WTGOperatingPoint(node_id='wtg:T1', active_power_mw=5.0, reactive_power_mvar=0.0),))
repair_workflow = optimise_project(repair_input, replace(cfg, scenario=ScenarioGenerationConfig(candidate_count=1), electrical=electrical))
candidate = repair_workflow.candidates[0]
api = to_api_response(repair_workflow, request_id='AUDIT', project_id=repair_input.project_id)
result['real_closed_loop_repair'] = {
    'status': repair_workflow.status.value,
    'initial_sizing_cables': dict(candidate.cable_sizing.segment_cable_type_ids) if candidate.cable_sizing else None,
    'repair_actions': [{'segment': a.segment_id, 'from': a.original_cable_type_id, 'to': a.upgraded_cable_type_id} for a in candidate.repair_log],
    'final_max_voltage_pu': candidate.load_flow_result.maximum_voltage_pu if candidate.load_flow_result else None,
    'presentation_repair_log_length': len(repair_workflow.recommended_result.recommended_candidate_repair_log) if repair_workflow.recommended_result else None,
    'segment_geojson_has_cable_type': [any('cable_type' in k for k in f['properties']) for f in repair_workflow.recommended_result.feature_collection['features'] if f['properties'].get('feature_type') == 'pnc_segment'] if repair_workflow.recommended_result else None,
}
model = Path('artifacts/ml/pre_ranker_v1/model.joblib')
metadata = json.loads(model.with_name('metadata.json').read_text())
result['artifact_hash_matches_metadata'] = hashlib.sha256(model.read_bytes()).hexdigest() == metadata['model_sha256']
no_poles = optimise_project(inp, replace(cfg, pole=None))
result['missing_pole_config'] = {'status': no_poles.status.value, 'failure_codes': [f.code.value for c in no_poles.candidates if c.engineering_assessment for f in c.engineering_assessment.extraction_failures]}
print(json.dumps(result, indent=2))
Path(__file__).with_name('surge_audit_probe_results.json').write_text(json.dumps(result, indent=2), encoding='utf-8')
