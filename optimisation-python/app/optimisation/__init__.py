"""Scenario generation package for SURGE-PY-017.

Public API
----------
generate_pnc_scenarios
    Generate a configurable set of deterministic PNC network candidates.

ScenarioGenerationConfig
    Controls candidate count and base seed.

PNCScenario
    One candidate network with its generation parameters and structural metrics.

ScenarioParameters
    Full description of algorithm inputs for one candidate.

ScenarioGenerationResult
    Return type including candidates and per-attempt diagnostics.

Errors
------
ScenarioGenerationError
    Base class for all scenario generation failures.
NoValidScenarioError
    Zero candidates could be generated.
InvalidScenarioConfigError
    Configuration failed validation.
"""

from app.algorithms.wtg_grouping import GroupingObjective
from app.optimisation.scenario_models import (
    AttemptOutcome,
    NoValidScenarioError,
    InvalidScenarioConfigError,
    PNCScenario,
    ScenarioAttempt,
    ScenarioGenerationConfig,
    ScenarioGenerationError,
    ScenarioGenerationResult,
    ScenarioParameters,
    ScenarioStrategy,
    TopologyWeightProfile,
)
from app.optimisation.scenarios import generate_pnc_scenarios, scenario_fingerprint

__all__ = [
    "AttemptOutcome",
    "GroupingObjective",
    "InvalidScenarioConfigError",
    "NoValidScenarioError",
    "PNCScenario",
    "ScenarioAttempt",
    "ScenarioGenerationConfig",
    "ScenarioGenerationError",
    "ScenarioGenerationResult",
    "ScenarioParameters",
    "ScenarioStrategy",
    "TopologyWeightProfile",
    "generate_pnc_scenarios",
    "scenario_fingerprint",
]
