"""WP2-2 — Characterise V0 scoring defaults.

Pins the default scoring policy values and the legacy weight mapping for the
four Java scenarios so any later package that changes them must pass through
a CCR.

The four legacy scenarios each send a ``ScoringWeightsRequest`` with these
specific weights.  Python maps them to ``CandidateScoringConfig`` with
``LEGACY_COMPATIBILITY`` policy mode, zero spatial and infrastructure group
weights, and electrical subweights normalised from the raw loss / loading /
margin weights.
"""

import math
from typing import Any

import pytest

from app.optimisation.scoring_models import (
    CandidateScoringConfig,
    ScoringPolicyMode,
)
from app.schemas.legacy_mapping import legacy_to_workflow_invocation
from app.schemas.optimise import OptimisationRequest
from app.schemas.v2.optimise import ScoringWeightsRequest

# ── Java ScenarioProfile weight tables (from ScenarioProfile.java) ──────────
# Each maps to a ScoringWeightsRequest for the V1 legacy path.

SCENARIO_WEIGHTS: dict[str, dict[str, float]] = {
    "Balanced": {
        "route_length_weight": 0.40,
        "electrical_loss_weight": 0.25,
        "cable_loading_weight": 0.20,
        "voltage_margin_weight": 0.15,
    },
    "Minimum Cost": {
        "route_length_weight": 0.70,
        "electrical_loss_weight": 0.12,
        "cable_loading_weight": 0.10,
        "voltage_margin_weight": 0.08,
    },
    "Minimum Land Impact": {
        "route_length_weight": 0.40,
        "electrical_loss_weight": 0.25,
        "cable_loading_weight": 0.20,
        "voltage_margin_weight": 0.15,
    },
    "Minimum Environmental Impact": {
        "route_length_weight": 0.40,
        "electrical_loss_weight": 0.25,
        "cable_loading_weight": 0.20,
        "voltage_margin_weight": 0.15,
    },
}

# ── ScoringWeightsRequest defaults (from app/schemas/v2/optimise.py) ────────

DEFAULT_SCORING_WEIGHTS = {
    "route_length_weight": 0.4,
    "electrical_loss_weight": 0.25,
    "cable_loading_weight": 0.20,
    "voltage_margin_weight": 0.15,
}


def _minimal_v1_payload(
    scenario: str,
    scoring_weights: dict[str, float] | None = None,
) -> dict[str, Any]:
    """Build the smallest valid V1 OptimisationRequest payload for a scenario."""
    weights = scoring_weights or DEFAULT_SCORING_WEIGHTS
    return {
        "request_id": f"REQ-V0-{scenario.replace(' ', '-')}",
        "project_id": "V0-SCORING-TEST",
        "scenario": scenario,
        "wtg_geojson": {
            "type": "FeatureCollection",
            "features": [
                {
                    "type": "Feature",
                    "geometry": {"type": "Point", "coordinates": [-1.0, 52.0]},
                    "properties": {"turbine_id": "T01", "capacity_mw": 5.0},
                }
            ],
        },
        "substation_geojson": {
            "type": "FeatureCollection",
            "features": [
                {
                    "type": "Feature",
                    "geometry": {"type": "Point", "coordinates": [-1.0, 52.002]},
                    "properties": {"substation_id": "SUB1"},
                }
            ],
        },
        "scoring_weights": weights,
    }


def _extract_scoring_config(
    scenario: str,
    scoring_weights: dict[str, float] | None = None,
) -> CandidateScoringConfig:
    """Build a V1 request and extract the scoring config from the invocation."""
    payload_dict = _minimal_v1_payload(scenario, scoring_weights)
    payload = OptimisationRequest(**payload_dict)
    invocation = legacy_to_workflow_invocation(payload)
    return invocation.config.scoring


class TestV0ScoringDefaults:
    """Pin the V0 scoring configuration produced by the legacy mapping."""

    @pytest.mark.parametrize("scenario", list(SCENARIO_WEIGHTS.keys()))
    def test_policy_mode_is_legacy_compatibility(self, scenario: str) -> None:
        config = _extract_scoring_config(scenario, SCENARIO_WEIGHTS[scenario])
        assert config.policy_mode == ScoringPolicyMode.LEGACY_COMPATIBILITY

    @pytest.mark.parametrize("scenario", list(SCENARIO_WEIGHTS.keys()))
    def test_spatial_weight_is_zero(self, scenario: str) -> None:
        config = _extract_scoring_config(scenario, SCENARIO_WEIGHTS[scenario])
        assert config.spatial_weight == 0.0

    @pytest.mark.parametrize("scenario", list(SCENARIO_WEIGHTS.keys()))
    def test_infrastructure_weight_is_zero(self, scenario: str) -> None:
        config = _extract_scoring_config(scenario, SCENARIO_WEIGHTS[scenario])
        assert config.infrastructure_weight == 0.0

    @pytest.mark.parametrize(
        "scenario,expected_physical,expected_electrical",
        [
            ("Balanced", 0.40, 0.60),
            ("Minimum Cost", 0.70, 0.30),
            ("Minimum Land Impact", 0.40, 0.60),
            ("Minimum Environmental Impact", 0.40, 0.60),
        ],
    )
    def test_group_weights(
        self,
        scenario: str,
        expected_physical: float,
        expected_electrical: float,
    ) -> None:
        config = _extract_scoring_config(scenario, SCENARIO_WEIGHTS[scenario])
        assert math.isclose(
            config.physical_weight, expected_physical, rel_tol=1e-12
        ), f"physical_weight for {scenario}"
        assert math.isclose(
            config.electrical_weight, expected_electrical, rel_tol=1e-12
        ), f"electrical_weight for {scenario}"
        # Sum must be 1.0
        total = math.fsum([
            config.physical_weight,
            config.spatial_weight,
            config.infrastructure_weight,
            config.electrical_weight,
        ])
        assert math.isclose(total, 1.0, rel_tol=1e-9)

    @pytest.mark.parametrize(
        "scenario,loss,loading,margin",
        [
            ("Balanced", 0.25, 0.20, 0.15),
            ("Minimum Cost", 0.12, 0.10, 0.08),
            ("Minimum Land Impact", 0.25, 0.20, 0.15),
            ("Minimum Environmental Impact", 0.25, 0.20, 0.15),
        ],
    )
    def test_electrical_subweights_normalised(
        self,
        scenario: str,
        loss: float,
        loading: float,
        margin: float,
    ) -> None:
        """Verify that the electrical subweights are normalised from the raw
        Java weights (each raw weight / sum of electrical weights)."""
        config = _extract_scoring_config(scenario, SCENARIO_WEIGHTS[scenario])
        elec_sum = loss + loading + margin

        expected_loss_sub = loss / elec_sum
        expected_loading_sub = loading / elec_sum
        expected_margin_sub = margin / elec_sum

        assert math.isclose(
            config.electrical_subweights.active_loss,
            expected_loss_sub,
            rel_tol=1e-12,
        )
        assert math.isclose(
            config.electrical_subweights.cable_loading,
            expected_loading_sub,
            rel_tol=1e-12,
        )
        assert math.isclose(
            config.electrical_subweights.voltage_margin,
            expected_margin_sub,
            rel_tol=1e-12,
        )

    @pytest.mark.parametrize("scenario", list(SCENARIO_WEIGHTS.keys()))
    def test_spatial_subweights_all_zero(self, scenario: str) -> None:
        config = _extract_scoring_config(scenario, SCENARIO_WEIGHTS[scenario])
        assert config.spatial_subweights.traversal_cost == 0.0
        assert config.spatial_subweights.affected_parcels == 0.0
        assert config.spatial_subweights.road_crossings == 0.0
        assert config.spatial_subweights.soft_overlap_length == 0.0
        assert config.spatial_subweights.owner_interactions == 0.0


class TestScoringWeightsRequestDefaults:
    """Pin the ScoringWeightsRequest Pydantic defaults used when Java sends
    no explicit weights."""

    def test_default_values(self) -> None:
        defaults = ScoringWeightsRequest()
        assert defaults.route_length_weight == 0.4
        assert defaults.electrical_loss_weight == 0.25
        assert defaults.cable_loading_weight == 0.20
        assert defaults.voltage_margin_weight == 0.15

    def test_default_sum_is_one(self) -> None:
        defaults = ScoringWeightsRequest()
        total = math.fsum([
            defaults.route_length_weight,
            defaults.electrical_loss_weight,
            defaults.cable_loading_weight,
            defaults.voltage_margin_weight,
        ])
        assert math.isclose(total, 1.0, rel_tol=1e-9)

    def test_default_matches_balanced_scenario(self) -> None:
        """The Pydantic defaults must match Java's Balanced profile."""
        defaults = ScoringWeightsRequest()
        balanced = SCENARIO_WEIGHTS["Balanced"]
        assert defaults.route_length_weight == balanced["route_length_weight"]
        assert defaults.electrical_loss_weight == balanced["electrical_loss_weight"]
        assert defaults.cable_loading_weight == balanced["cable_loading_weight"]
        assert defaults.voltage_margin_weight == balanced["voltage_margin_weight"]
