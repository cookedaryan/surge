"""PNC Network Assembly package.

Provides the orchestration layer that converts individually generated
feeder networks into one complete Project PNC Network.

Two entry points
----------------
build_pnc_network
    Full pipeline from raw project data: grouping → topology → routing →
    refinement → assembly.
assemble_pnc_network
    Assembly from pre-computed topology and refined routes.  No routing
    algorithms are re-executed.  Use inside OptimisationService or any
    caller that already holds both intermediate results.
"""

from app.pnc.assembly import assemble_pnc_network, build_pnc_network
from app.pnc.errors import PNCAssemblyError, PNCAssemblyErrorCode
from app.pnc.geojson import network_to_feature_collection
from app.pnc.models import PNCFeeder, PNCSegment, ProjectPNCNetwork

__all__ = [
    "assemble_pnc_network",
    "build_pnc_network",
    "network_to_feature_collection",
    "PNCAssemblyError",
    "PNCAssemblyErrorCode",
    "PNCFeeder",
    "PNCSegment",
    "ProjectPNCNetwork",
]
