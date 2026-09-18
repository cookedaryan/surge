"""Geometry fingerprint canonicaliser. Owned by L3 (WP0B-7).

Ordered projected features after declared CRS, axis order, units, precision
quantisation, orientation and empty-geometry rules.
Output format: ``geometry:<version>:<sha256>``.

Canonicalisation rules, version 1
---------------------------------
Input is a ``ProjectPNCNetwork`` (or a ``PNCScenario``, whose ``network`` is
used): the substation point, every WTG point and every routed segment line.

* **CRS.** Coordinates are taken in the network's own projected CRS, which must
  carry an EPSG code, one east and one north axis, and metre units. The code is
  part of the hash, so the same numbers in another CRS are another geometry.
  Nothing is reprojected: reprojection would add floating-point noise.
* **Axis order.** ``x`` is easting and ``y`` is northing, whatever the CRS
  authority's axis order, because every transformer in this service is built
  with ``always_xy=True``.
* **Units and precision.** Each ordinate is quantised to whole millimetres,
  rounding half to even on the exact binary value, and written as an integer.
* **Dimensions.** Only 2D geometry is accepted; a Z ordinate is rejected.
* **Orientation.** A cable has no direction: a line is written in whichever
  direction, forwards or reversed, is lexicographically smaller.
* **Vertices.** Consecutive vertices that quantise to the same millimetre are
  collapsed into one.
* **Empty geometry.** Empty points and lines, non-finite ordinates, lines that
  collapse to fewer than two vertices, and networks without segments are
  rejected with ``GeometryFingerprintError``; they are never hashed.
* **Order and identity.** WTG points and lines are sorted by their canonical
  coordinates. Feature IDs, feeder IDs and segment IDs are not hashed, because
  they are labels, not geometry. Duplicate lines are kept.

Any change to these rules is a new ``GEOMETRY_FINGERPRINT_VERSION``.
"""

import math
from collections.abc import Iterable
from decimal import ROUND_HALF_EVEN, Decimal
from typing import Any, Literal

from pyproj import CRS
from shapely.geometry import LineString, Point

from app.contracts.canonical_json import canonical_sha256
from app.optimisation.scenario_models import PNCScenario
from app.pnc.models import ProjectPNCNetwork

GEOMETRY_FINGERPRINT_VERSION = "1"

QUANTUM_M = Decimal("0.001")
_UNITS_PER_METRE = 1000

CanonicalVertex = tuple[int, int]
CanonicalLine = tuple[CanonicalVertex, ...]


class GeometryFingerprintError(ValueError):
    """Raised when a design's geometry breaks a declared canonicalisation rule."""


def network_of(design: object) -> ProjectPNCNetwork:
    """Return the network a fingerprint is computed over."""
    if isinstance(design, PNCScenario):
        return design.network
    if isinstance(design, ProjectPNCNetwork):
        return design
    raise TypeError(
        "Geometry fingerprints need a ProjectPNCNetwork or PNCScenario, "
        f"not {type(design).__name__}"
    )


def canonical_crs(crs: CRS) -> str:
    """Return the declared CRS identity, or raise when the CRS is not allowed."""
    if not crs.is_projected:
        raise GeometryFingerprintError(f"CRS {crs.name!r} is not projected")
    epsg = crs.to_epsg()
    if epsg is None:
        raise GeometryFingerprintError(f"CRS {crs.name!r} has no EPSG code")
    directions = sorted(axis.direction.lower() for axis in crs.axis_info)
    if directions != ["east", "north"]:
        raise GeometryFingerprintError(
            f"EPSG:{epsg} axes are {directions}, expected one east and one north"
        )
    units = {axis.unit_name.lower() for axis in crs.axis_info}
    if not units <= {"metre", "meter"}:
        raise GeometryFingerprintError(
            f"EPSG:{epsg} units are {sorted(units)}, expected metres"
        )
    return f"EPSG:{epsg}"


def _quantise(value: float) -> int:
    if not math.isfinite(value):
        raise GeometryFingerprintError(f"non-finite ordinate {value!r}")
    millimetres = Decimal(value).quantize(QUANTUM_M, rounding=ROUND_HALF_EVEN)
    return int(millimetres * _UNITS_PER_METRE)


def _vertices(coords: Iterable[tuple[float, ...]]) -> list[CanonicalVertex]:
    vertices: list[CanonicalVertex] = []
    for coord in coords:
        vertices.append((_quantise(coord[0]), _quantise(coord[1])))
    return vertices


def canonical_point(point: Point) -> CanonicalVertex:
    if point.is_empty:
        raise GeometryFingerprintError("empty point")
    if point.has_z:
        raise GeometryFingerprintError("3D point; only 2D geometry is accepted")
    return _quantise(point.x), _quantise(point.y)


def canonical_line(line: LineString) -> CanonicalLine:
    """Quantise, collapse repeated vertices and orient one routed line."""
    if line.is_empty:
        raise GeometryFingerprintError("empty line")
    if line.has_z:
        raise GeometryFingerprintError("3D line; only 2D geometry is accepted")
    collapsed: list[CanonicalVertex] = []
    for vertex in _vertices(line.coords):
        if not collapsed or collapsed[-1] != vertex:
            collapsed.append(vertex)
    if len(collapsed) < 2:
        raise GeometryFingerprintError(
            "line collapses to a single vertex at millimetre precision"
        )
    forwards = tuple(collapsed)
    backwards = tuple(reversed(collapsed))
    return min(forwards, backwards)


def canonical_geometry_payload(network: ProjectPNCNetwork) -> dict[str, Any]:
    """Return the canonical JSON value the geometry fingerprint hashes."""
    lines = [
        canonical_line(segment.route_geometry)
        for feeder in network.feeders
        for segment in feeder.segments
    ]
    if not lines:
        raise GeometryFingerprintError("network has no routed segments")
    turbines = sorted(canonical_point(p) for p in network.wtg_coordinates.values())
    return {
        "canonicaliser": "geometry",
        "version": GEOMETRY_FINGERPRINT_VERSION,
        "crs": canonical_crs(network.crs),
        "axis_order": "easting,northing",
        "unit": "mm",
        "substation": list(canonical_point(network.substation_geometry)),
        "turbines": [list(vertex) for vertex in turbines],
        "lines": [[list(vertex) for vertex in line] for line in sorted(lines)],
    }


class GeometryFingerprinter:
    kind: Literal["geometry"] = "geometry"
    version = GEOMETRY_FINGERPRINT_VERSION

    def __call__(self, design: object) -> str:
        payload = canonical_geometry_payload(network_of(design))
        return f"{self.kind}:{self.version}:{canonical_sha256(payload)}"
