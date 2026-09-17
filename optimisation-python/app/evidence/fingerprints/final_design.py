"""Final-design fingerprint canonicaliser. Owned by L3 (WP0B-6).

Geometry fingerprint plus final installed conductor assignments and other
explicitly versioned installed fields. This is the identity the strong claim
uses. Output format: ``final_design:<version>:<sha256>``.

Canonicalisation rules, version 1
---------------------------------
Input is a ``FinalDesign``: the routed network and its C2 ``design_truth``.

* **Geometry.** The version 1 geometry fingerprint of the network is hashed
  as-is, so every geometry rule applies here too.
* **Installed fields** (``INSTALLED_FIELDS``):
  ``final_cable_type_id`` per routed segment, and ``feeder_circuit``, the set
  of segments wired into each feeder. Each segment is keyed by its canonical
  geometry line, not by its segment ID.
* **Not hashed.** Candidate, feeder and segment IDs (labels), the initial
  conductor, the ``repaired`` flag, repair actions (history, not installed
  state), the sizing-basis label, and poles (derived from the routed geometry
  and not yet published as installed truth).
* **Order.** Segments within a feeder circuit, then feeder circuits, are sorted
  by canonical content.
* **Completeness.** ``design_truth`` must list every routed segment exactly once,
  under the segment's own feeder, with a non-empty final conductor. Anything
  else raises ``FinalDesignFingerprintError``.

Adding a field to ``INSTALLED_FIELDS`` or changing a rule is a new
``FINAL_DESIGN_FINGERPRINT_VERSION``.
"""

from dataclasses import dataclass
from typing import Any, Literal

from app.contracts.canonical_json import canonical_sha256
from app.contracts.response import DesignTruth
from app.evidence.fingerprints.geometry import (
    GeometryFingerprinter,
    canonical_line,
    network_of,
)
from app.optimisation.scenario_models import PNCScenario
from app.pnc.models import ProjectPNCNetwork

FINAL_DESIGN_FINGERPRINT_VERSION = "1"

INSTALLED_FIELDS: tuple[str, ...] = ("final_cable_type_id", "feeder_circuit")


class FinalDesignFingerprintError(ValueError):
    """Raised when design truth does not describe the routed network exactly."""


@dataclass(frozen=True)
class FinalDesign:
    """A routed network together with what was installed on it."""

    network: ProjectPNCNetwork | PNCScenario
    design_truth: DesignTruth


def _installed_by_segment(
    network: ProjectPNCNetwork, truth: DesignTruth
) -> dict[str, str]:
    installed: dict[str, str] = {}
    for record in truth.segments:
        if record.segment_id in installed:
            raise FinalDesignFingerprintError(
                f"design truth lists segment {record.segment_id} more than once"
            )
        if not record.final_cable_type_id.strip():
            raise FinalDesignFingerprintError(
                f"segment {record.segment_id} has an empty final conductor"
            )
        installed[record.segment_id] = record.final_cable_type_id

    feeder_of = {record.segment_id: record.feeder_id for record in truth.segments}
    routed = {
        segment.segment_id: segment.feeder_id
        for feeder in network.feeders
        for segment in feeder.segments
    }
    missing = sorted(routed.keys() - installed.keys())
    unknown = sorted(installed.keys() - routed.keys())
    if missing or unknown:
        raise FinalDesignFingerprintError(
            "design truth does not match the routed segments: "
            f"missing {missing}, unknown {unknown}"
        )
    moved = sorted(sid for sid, fid in routed.items() if feeder_of[sid] != fid)
    if moved:
        raise FinalDesignFingerprintError(
            f"design truth places segments under another feeder: {moved}"
        )
    return installed


def canonical_final_design_payload(design: FinalDesign) -> dict[str, Any]:
    """Return the canonical JSON value the final-design fingerprint hashes."""
    network = network_of(design.network)
    installed = _installed_by_segment(network, design.design_truth)
    circuits = sorted(
        sorted(
            [
                [list(vertex) for vertex in canonical_line(segment.route_geometry)],
                installed[segment.segment_id],
            ]
            for segment in feeder.segments
        )
        for feeder in network.feeders
        if feeder.segments
    )
    return {
        "canonicaliser": "final_design",
        "version": FINAL_DESIGN_FINGERPRINT_VERSION,
        "geometry": GeometryFingerprinter()(network),
        "installed_fields": list(INSTALLED_FIELDS),
        "feeder_circuits": circuits,
    }


class FinalDesignFingerprinter:
    kind: Literal["final_design"] = "final_design"
    version = FINAL_DESIGN_FINGERPRINT_VERSION

    def __call__(self, design: object) -> str:
        if not isinstance(design, FinalDesign):
            raise TypeError(
                "Final-design fingerprints need a FinalDesign, "
                f"not {type(design).__name__}"
            )
        payload = canonical_final_design_payload(design)
        return f"{self.kind}:{self.version}:{canonical_sha256(payload)}"
