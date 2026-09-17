"""Topology fingerprint canonicaliser. Owned by L2 (WP0B-5).

Sorted logical nodes and edges plus feeder membership, independent of transient
IDs and serialisation order. Output format: ``topology:<version>:<sha256>``.
"""

from typing import Literal

TOPOLOGY_FINGERPRINT_VERSION = "1"


class TopologyFingerprinter:
    kind: Literal["topology"] = "topology"
    version = TOPOLOGY_FINGERPRINT_VERSION

    def __call__(self, design: object) -> str:
        raise NotImplementedError("Implemented by WP0B-5 (L2)")
