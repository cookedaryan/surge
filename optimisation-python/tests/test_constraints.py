import numpy as np
import pytest
from affine import Affine
from pyproj import CRS, Transformer
from shapely.geometry import LineString, Point, Polygon

from app.algorithms.a_star import a_star
from app.algorithms.physical_routing import PhysicalRoute
from app.algorithms.route_refinement import (
    refine_physical_route,
    segment_supercover_cells,
)
from app.gis.constraints import (
    ConstraintLayer,
    ConstraintMode,
    ConstraintType,
    apply_avoidance_constraints,
    apply_constraint_layers,
    parse_constraint_layers,
)
from app.gis.cost_surface import CostSurface, grid_to_world, world_to_grid
from app.gis.preprocessing import validate_project_routing_endpoints
from app.models.spatial import ProjectSpatialData, Substation, WindTurbine


def _surface() -> CostSurface:
    return CostSurface(
        costs=np.ones((20, 20), dtype=np.float32),
        transform=Affine.translation(500000.0, 1000.0) * Affine.scale(10.0, -10.0),
        crs=CRS("EPSG:32631"),
        width=20,
        height=20,
        resolution_m=10.0,
    )


def test_polygon_is_rasterized_as_blocked_cells() -> None:
    surface = _surface()
    to_wgs84 = Transformer.from_crs(surface.crs, CRS("EPSG:4326"), always_xy=True)
    corners = [
        to_wgs84.transform(x, y)
        for x, y in (
            (500070.0, 930.0),
            (500130.0, 930.0),
            (500130.0, 870.0),
            (500070.0, 870.0),
            (500070.0, 930.0),
        )
    ]
    result = apply_avoidance_constraints(
        surface,
        {
            "type": "FeatureCollection",
            "features": [
                {
                    "type": "Feature",
                    "properties": {"layer_type": "restricted_land"},
                    "geometry": {"type": "Polygon", "coordinates": [corners]},
                }
            ],
        },
        buffer_m=0.0,
    )

    blocked_row, blocked_col = world_to_grid(500100.0, 900.0, result)
    clear_row, clear_col = world_to_grid(500020.0, 980.0, result)
    assert np.isinf(result.costs[blocked_row, blocked_col])
    assert result.costs[clear_row, clear_col] == pytest.approx(1.0)
    assert np.all(surface.costs == 1.0)


def test_avoidance_collection_rejects_point_geometry() -> None:
    with pytest.raises(ValueError, match="Avoidance geometries"):
        apply_avoidance_constraints(
            _surface(),
            {
                "type": "FeatureCollection",
                "features": [
                    {
                        "type": "Feature",
                        "properties": {},
                        "geometry": {"type": "Point", "coordinates": [3.0, 0.0]},
                    }
                ],
            },
            buffer_m=10.0,
        )


def test_road_defaults_to_finite_soft_penalty() -> None:
    surface = _surface()
    to_wgs84 = Transformer.from_crs(surface.crs, CRS("EPSG:4326"), always_xy=True)
    coordinates = [
        to_wgs84.transform(500100.0, 990.0),
        to_wgs84.transform(500100.0, 810.0),
    ]
    result = apply_avoidance_constraints(
        surface,
        {
            "type": "FeatureCollection",
            "features": [
                {
                    "type": "Feature",
                    "properties": {
                        "constraint_id": "road-1",
                        "constraint_type": "ROAD",
                    },
                    "geometry": {"type": "LineString", "coordinates": coordinates},
                }
            ],
        },
        buffer_m=0.0,
        soft_cost_weight=7.5,
    )

    row, col = world_to_grid(500100.0, 900.0, result)
    assert result.costs[row, col] == pytest.approx(8.5)
    assert np.isfinite(result.costs).all()
    assert np.all(surface.costs == 1.0)


def test_feature_order_does_not_change_raster() -> None:
    surface = _surface()
    to_wgs84 = Transformer.from_crs(surface.crs, CRS("EPSG:4326"), always_xy=True)

    def feature(layer_id: str, x: float, cost_weight: float) -> dict[str, object]:
        return {
            "type": "Feature",
            "properties": {
                "constraint_id": layer_id,
                "constraint_type": "PARCEL",
                "cost_weight": cost_weight,
            },
            "geometry": {
                "type": "Polygon",
                "coordinates": [
                    [
                        to_wgs84.transform(x, 960.0),
                        to_wgs84.transform(x + 60.0, 960.0),
                        to_wgs84.transform(x + 60.0, 840.0),
                        to_wgs84.transform(x, 840.0),
                        to_wgs84.transform(x, 960.0),
                    ]
                ],
            },
        }

    first = feature("parcel-b", 500060.0, 3.25)
    second = feature("parcel-a", 500100.0, 6.75)
    forward = apply_avoidance_constraints(
        surface,
        {"type": "FeatureCollection", "features": [first, second]},
        buffer_m=0.0,
    )
    reverse = apply_avoidance_constraints(
        surface,
        {"type": "FeatureCollection", "features": [second, first]},
        buffer_m=0.0,
    )

    assert np.array_equal(forward.costs, reverse.costs)


def test_implicit_layer_ids_are_content_stable() -> None:
    surface = _surface()
    to_wgs84 = Transformer.from_crs(surface.crs, CRS("EPSG:4326"), always_xy=True)
    features = [
        {
            "type": "Feature",
            "properties": {"constraint_type": "ROAD"},
            "geometry": {
                "type": "LineString",
                "coordinates": [
                    to_wgs84.transform(500050.0, 990.0),
                    to_wgs84.transform(500050.0, 810.0),
                ],
            },
        },
        {
            "type": "Feature",
            "properties": {"constraint_type": "ROAD"},
            "geometry": {
                "type": "LineString",
                "coordinates": [
                    to_wgs84.transform(500150.0, 990.0),
                    to_wgs84.transform(500150.0, 810.0),
                ],
            },
        },
    ]

    forward = parse_constraint_layers(
        {"type": "FeatureCollection", "features": features},
        target_crs=surface.crs,
        default_buffer_m=0.0,
        default_soft_cost_weight=20.0,
    )
    reverse = parse_constraint_layers(
        {"type": "FeatureCollection", "features": list(reversed(features))},
        target_crs=surface.crs,
        default_buffer_m=0.0,
        default_soft_cost_weight=20.0,
    )

    assert [(layer.layer_id, layer.geometry.wkb) for layer in forward] == [
        (layer.layer_id, layer.geometry.wkb) for layer in reverse
    ]


def test_explicit_no_go_overrides_soft_type_default() -> None:
    surface = _surface()
    to_wgs84 = Transformer.from_crs(surface.crs, CRS("EPSG:4326"), always_xy=True)
    coordinates = [
        to_wgs84.transform(500100.0, 990.0),
        to_wgs84.transform(500100.0, 810.0),
    ]
    layers = parse_constraint_layers(
        {
            "type": "FeatureCollection",
            "features": [
                {
                    "type": "Feature",
                    "properties": {
                        "constraint_id": "road-no-go",
                        "constraint_type": "ROAD",
                        "routing_mode": "HARD_EXCLUSION",
                    },
                    "geometry": {"type": "LineString", "coordinates": coordinates},
                }
            ],
        },
        target_crs=surface.crs,
        default_buffer_m=10.0,
        default_soft_cost_weight=20.0,
    )

    assert layers[0].mode == ConstraintMode.HARD_EXCLUSION
    assert layers[0].cost_weight is None


def test_project_endpoint_inside_hard_exclusion_is_rejected() -> None:
    surface = _surface()
    project = ProjectSpatialData(
        turbines=(
            WindTurbine(
                turbine_id="WTG-1",
                location=Point(500100.0, 900.0),
                capacity_mw=5.0,
            ),
        ),
        substation=Substation(
            substation_id="SUB-1",
            location=Point(500020.0, 980.0),
        ),
        projected_crs=surface.crs,
    )
    hard_layer = ConstraintLayer(
        layer_id="restricted-1",
        layer_type=ConstraintType.RESTRICTED_AREA,
        mode=ConstraintMode.HARD_EXCLUSION,
        geometry=Polygon(
            [
                (500080.0, 920.0),
                (500120.0, 920.0),
                (500120.0, 880.0),
                (500080.0, 880.0),
            ]
        ),
        buffer_m=0.0,
        cost_weight=None,
        crs=surface.crs,
    )
    constrained = apply_constraint_layers(surface, (hard_layer,))

    with pytest.raises(ValueError, match="WTG WTG-1 lies inside hard exclusion"):
        validate_project_routing_endpoints(project, constrained, (hard_layer,))


def test_refined_route_never_touches_hard_constraint_cells() -> None:
    surface = _surface()
    hard_layer = ConstraintLayer(
        layer_id="restricted-1",
        layer_type=ConstraintType.RESTRICTED_AREA,
        mode=ConstraintMode.HARD_EXCLUSION,
        geometry=Polygon(
            [
                (500080.0, 970.0),
                (500120.0, 970.0),
                (500120.0, 850.0),
                (500080.0, 850.0),
            ]
        ),
        buffer_m=0.0,
        cost_weight=None,
        crs=surface.crs,
    )
    constrained = apply_constraint_layers(surface, (hard_layer,))
    start = (10, 2)
    goal = (10, 17)
    path = a_star(constrained, start, goal)
    assert path is not None
    geometry = LineString(
        [grid_to_world(row, col, constrained) for row, col in path.path]
    )
    refined = refine_physical_route(
        PhysicalRoute(
            feeder_id="FDR-1",
            start_node_id="SUB-1",
            end_node_id="WTG-1",
            geometry=geometry,
            length_m=geometry.length,
            traversal_cost=path.traversal_cost,
        ),
        constrained,
    )

    for start_coordinate, end_coordinate in zip(
        refined.geometry.coords,
        tuple(refined.geometry.coords)[1:],
        strict=False,
    ):
        touched = segment_supercover_cells(
            start_coordinate,
            end_coordinate,
            constrained,
        )
        assert all(np.isfinite(constrained.costs[row, col]) for row, col in touched)


def _typed_feature(feature_id: str, feature_type: object) -> dict[str, object]:
    properties: dict[str, object] = {
        "constraint_id": feature_id,
        "constraint_type": "restricted_area",
        "routing_mode": "hard",
        "source_id": "asset-" + feature_id,
    }
    if feature_type is not None:
        properties["feature_type"] = feature_type
    return {
        "type": "Feature",
        "geometry": {
            "type": "Polygon",
            "coordinates": [
                [[2.0, 0.009], [2.001, 0.009], [2.001, 0.010], [2.0, 0.009]]
            ],
        },
        "properties": properties,
    }


def _parse_typed(feature_type: object) -> ConstraintLayer:
    layers = parse_constraint_layers(
        {"type": "FeatureCollection", "features": [_typed_feature("f1", feature_type)]},
        target_crs=CRS("EPSG:32631"),
        default_buffer_m=0.0,
        default_soft_cost_weight=2.0,
    )
    assert len(layers) == 1
    return layers[0]


# WP2-4: C1 typed identity is resolved at parse time, so everything downstream
# reads one canonical vocabulary rather than whatever spelling the caller used.


def test_feature_type_aliases_resolve_to_canonical_values() -> None:
    assert _parse_typed("RESERVE FOREST").feature_type == "forest"
    assert _parse_typed("Reserve-Forest").feature_type == "forest"
    assert _parse_typed("wildlife_sanctuary").feature_type == "protected_area"
    assert _parse_typed("RESERVOIR").feature_type == "water_body"
    assert _parse_typed("village").feature_type == "settlement"


def test_forest_is_not_collapsed_into_protected_or_restricted_area() -> None:
    # Finding F7: these three were one value before typed identity existed.
    assert _parse_typed("forest").feature_type == "forest"
    assert _parse_typed("protected_area").feature_type == "protected_area"
    assert _parse_typed("restricted").feature_type == "restricted_area"


def test_source_id_survives_parsing() -> None:
    assert _parse_typed("forest").source_id == "asset-f1"


def test_unknown_or_absent_feature_type_is_none_not_a_guess() -> None:
    # Absent means V0. Unknown must not become a specific environmental class;
    # WP3-1 turns an unknown explicit value into a stable error.
    assert _parse_typed(None).feature_type is None
    assert _parse_typed("something_nobody_mapped").feature_type is None
    assert _parse_typed("   ").feature_type is None
    assert _parse_typed(42).feature_type is None


def test_typed_identity_does_not_change_routing_treatment() -> None:
    # constraint_type still selects the routing class, exactly as before.
    layer = _parse_typed("forest")
    assert layer.layer_type == ConstraintType.RESTRICTED_AREA
    assert layer.mode == ConstraintMode.HARD_EXCLUSION
