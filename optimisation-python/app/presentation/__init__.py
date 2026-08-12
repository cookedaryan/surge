"""Presentation layer for creating map-ready JSON result boundaries."""

from app.presentation.exceptions import PresentationDataMismatchError
from app.presentation.models import (
    ElectricalSummary,
    FeederResult,
    NetworkSummary,
    ProjectOptimizationResult,
    ViolationPresentation,
)
from app.presentation.result_builder import build_project_result

__all__ = [
    "PresentationDataMismatchError",
    "ProjectOptimizationResult",
    "NetworkSummary",
    "ElectricalSummary",
    "ViolationPresentation",
    "FeederResult",
    "build_project_result",
]
