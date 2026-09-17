"""Geometry fingerprint canonicaliser. Owned by L3 (WP0B-7).

Ordered projected features after declared CRS, axis order, units, precision
quantisation, orientation and empty-geometry rules.
Output format: ``geometry:<version>:<sha256>``.
"""

from typing import Literal

GEOMETRY_FINGERPRINT_VERSION = "1"


class GeometryFingerprinter:
    kind: Literal["geometry"] = "geometry"
    version = GEOMETRY_FINGERPRINT_VERSION

    def __call__(self, design: object) -> str:
        raise NotImplementedError("Implemented by WP0B-7 (L3)")
