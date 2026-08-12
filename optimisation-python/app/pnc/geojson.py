"""GeoJSON converter for the assembled PNC network.

Produces a standard GeoJSON FeatureCollection containing:
  - One Point feature per substation   (feature_type: "pnc_substation")
  - One Point feature per WTG          (feature_type: "pnc_wtg")
  - One LineString feature per segment (feature_type: "pnc_segment")

All geometry is re-projected from the network's projected CRS to WGS-84
(EPSG:4326) by default, so the output is directly renderable on a standard
web map.  Pass *output_crs=None* to skip CRS conversion and keep the
projected coordinates.
"""

from typing import Any

import pyproj

from app.gis.crs import WGS84_CRS, get_transformer, transform_geometry
from app.pnc.models import ProjectPNCNetwork


def network_to_feature_collection(
    network: ProjectPNCNetwork,
    output_crs: pyproj.CRS | None = WGS84_CRS,
) -> dict[str, Any]:
    """Convert a ``ProjectPNCNetwork`` to a GeoJSON FeatureCollection.

    Parameters
    ----------
    network:
        The assembled PNC network.  All geometry is expected to be in
        ``network.crs`` (the projected CRS used during optimisation).
    output_crs:
        Target CRS for the output coordinates.  Defaults to WGS-84
        (EPSG:4326).  Pass *None* to keep the projected CRS.

    Returns
    -------
    dict
        A GeoJSON FeatureCollection ready for serialisation.  All geometry is
        in *output_crs* (or the network's projected CRS if *output_crs* is
        *None*).
    """
    transformer = (
        get_transformer(network.crs, output_crs) if output_crs is not None else None
    )

    def _project_point(point: Any) -> list[float]:
        if transformer is None:
            return [point.x, point.y]
        transformed = transform_geometry(point, transformer)
        return [transformed.x, transformed.y]

    def _project_linestring(line: Any) -> list[list[float]]:
        if transformer is None:
            return [[x, y] for x, y in line.coords]
        transformed = transform_geometry(line, transformer)
        return [[x, y] for x, y in transformed.coords]

    features: list[dict[str, Any]] = []

    # ------------------------------------------------------------------ #
    # Substation feature                                                   #
    # ------------------------------------------------------------------ #
    features.append(
        {
            "type": "Feature",
            "properties": {
                "feature_type": "pnc_substation",
                "substation_id": network.substation_id,
                "project_id": network.project_id,
            },
            "geometry": {
                "type": "Point",
                "coordinates": _project_point(network.substation_geometry),
            },
        }
    )

    # ------------------------------------------------------------------ #
    # WTG features (one per turbine, sorted by wtg node ID for stability)  #
    # ------------------------------------------------------------------ #
    # Build a reverse lookup: wtg_node_id → feeder_id
    wtg_feeder_map: dict[str, str] = {}
    for feeder in network.feeders:
        for wtg_id in feeder.wtg_ids:
            wtg_feeder_map[wtg_id] = feeder.feeder_id

    for wtg_id in sorted(network.wtg_coordinates):
        point = network.wtg_coordinates[wtg_id]
        features.append(
            {
                "type": "Feature",
                "properties": {
                    "feature_type": "pnc_wtg",
                    "wtg_id": wtg_id,
                    "feeder_id": wtg_feeder_map.get(wtg_id, ""),
                    "project_id": network.project_id,
                },
                "geometry": {
                    "type": "Point",
                    "coordinates": _project_point(point),
                },
            }
        )

    # ------------------------------------------------------------------ #
    # Segment features (one per routed cable/pole segment, by segment_id)  #
    # ------------------------------------------------------------------ #
    all_segments = sorted(
        (seg for feeder in network.feeders for seg in feeder.segments),
        key=lambda s: s.segment_id,
    )
    for segment in all_segments:
        features.append(
            {
                "type": "Feature",
                "properties": {
                    "feature_type": "pnc_segment",
                    "segment_id": segment.segment_id,
                    "feeder_id": segment.feeder_id,
                    "from_node": segment.from_node_id,
                    "to_node": segment.to_node_id,
                    "length_m": round(segment.route_length_m, 3),
                    "segment_type": segment.segment_type,
                    "project_id": network.project_id,
                },
                "geometry": {
                    "type": "LineString",
                    "coordinates": _project_linestring(segment.route_geometry),
                },
            }
        )

    return {
        "type": "FeatureCollection",
        "features": features,
    }
