import math
from collections.abc import Sequence
from typing import Any

import pytest
from pyproj import CRS
from shapely.geometry import (
    LineString,
    MultiLineString,
    MultiPolygon,
    Polygon,
)

from app.algorithms.route_refinement import RefinedPhysicalRoute
from app.gis.row_analysis import (
    ConstraintFeature,
    ProjectConstraintLayers,
    RowAnalysisResult,
    RowConfig,
    analyse_row_corridors,
)

PROJECT_CRS = CRS("EPSG:32632")


def make_route(
    coordinates: Sequence[tuple[float, float]] = ((0.0, 0.0), (100.0, 0.0)),
    *,
    feeder_id: str = "F1",
    start_node_id: str = "A",
    end_node_id: str = "B",
    refined_length_m: float | None = None,
) -> RefinedPhysicalRoute:
    geometry = LineString(coordinates)
    length = float(geometry.length)
    return RefinedPhysicalRoute(
        feeder_id=feeder_id,
        start_node_id=start_node_id,
        end_node_id=end_node_id,
        geometry=geometry,
        original_length_m=length,
        refined_length_m=length if refined_length_m is None else refined_length_m,
        original_traversal_cost=length,
        refined_traversal_cost=length,
    )


def make_feature(
    feature_id: str,
    layer_type: Any,
    geometry: Any,
    severity: Any = None,
) -> ConstraintFeature:
    return ConstraintFeature(
        feature_id=feature_id,
        layer_type=layer_type,
        geometry=geometry,
        severity=severity,
    )


def analyse(  
    routes: tuple[RefinedPhysicalRoute, ...] = (make_route(),),
    features: tuple[ConstraintFeature, ...] = (),
    *,
    config: RowConfig | None = None,
    route_crs: CRS = PROJECT_CRS,
    constraint_crs: CRS = PROJECT_CRS,
) -> RowAnalysisResult:
    return analyse_row_corridors(
        routes,
        route_crs,
        ProjectConstraintLayers(features=features, crs=constraint_crs),
        config or RowConfig(corridor_width_m=20.0),
    )


def test_flat_row_buffer_has_configured_width_and_no_end_extension() -> None:
    result = analyse()
    corridor = result.corridors[0]

    assert corridor.row_geometry.bounds == pytest.approx((0.0, -10.0, 100.0, 10.0))
    assert corridor.corridor_width_m == 20.0


def test_row_area_and_route_metadata_are_preserved() -> None:
    result = analyse()
    corridor = result.corridors[0]

    assert corridor.row_area_m2 == pytest.approx(2_000.0)
    assert corridor.route_length_m == pytest.approx(100.0)
    assert corridor.feeder_id == "F1"
    assert corridor.start_node_id == "A"
    assert corridor.end_node_id == "B"


def test_empty_routes_and_constraints_return_empty_analysis() -> None:
    result = analyse(routes=())

    assert result.corridors == ()
    assert result.intersections == ()
    assert result.total_row_area_m2 == 0.0
    assert result.unique_row_footprint_area_m2 == 0.0


def test_distant_constraint_does_not_intersect() -> None:
    parcel = make_feature(
        "P1", "parcel", Polygon([(200, 200), (210, 200), (210, 210), (200, 210)])
    )

    result = analyse(features=(parcel,))

    assert result.intersections == ()
    assert result.unique_parcel_count == 0


def test_polygon_intersection_has_area_and_route_overlap_length() -> None:
    parcel = make_feature(
        "P1", "parcel", Polygon([(20, -5), (40, -5), (40, 5), (20, 5)])
    )

    result = analyse(features=(parcel,))
    intersection = result.intersections[0]

    assert intersection.intersection_area_m2 == pytest.approx(200.0)
    assert intersection.route_overlap_length_m == pytest.approx(20.0)
    assert intersection.intersection_length_m == pytest.approx(20.0)
    assert intersection.constraint_length_within_corridor_m == 0.0
    assert not intersection.touches_only


def test_multiple_constraints_are_ordered_deterministically() -> None:
    forest = make_feature(
        "FST", "forest", Polygon([(40, -5), (60, -5), (60, 5), (40, 5)])
    )
    parcel = make_feature(
        "P1", "parcel", Polygon([(20, -5), (30, -5), (30, 5), (20, 5)])
    )

    first = analyse(features=(parcel, forest))
    second = analyse(features=(forest, parcel))

    first_keys = [(item.layer_type, item.feature_id) for item in first.intersections]
    second_keys = [(item.layer_type, item.feature_id) for item in second.intersections]
    assert first_keys == second_keys == [("forest", "FST"), ("parcel", "P1")]


def test_same_parcel_across_routes_is_counted_once() -> None:
    routes = (
        make_route(end_node_id="B1"),
        make_route(
            ((0, 5), (100, 5)),
            feeder_id="F2",
            start_node_id="C",
            end_node_id="D",
        ),
    )
    parcel = make_feature(
        "P1", "parcel", Polygon([(20, -20), (40, -20), (40, 20), (20, 20)])
    )

    result = analyse(routes=routes, features=(parcel,))

    assert len(result.intersections) == 2
    assert result.unique_parcel_count == 1


def test_linear_road_crossing_is_counted_once() -> None:
    road = make_feature("R1", "road", LineString([(50, -100), (50, 100)]))

    result = analyse(features=(road,))
    intersection = result.intersections[0]

    assert result.road_crossing_count == 1
    assert intersection.constraint_length_within_corridor_m == pytest.approx(20.0)
    assert intersection.route_overlap_length_m == 0.0


def test_multiline_road_shared_vertex_is_deduplicated() -> None:
    road = make_feature(
        "R1",
        "road",
        MultiLineString(
            [
                [(50, -20), (50, 0)],
                [(50, 0), (50, 20)],
            ]
        ),
    )

    result = analyse(features=(road,))

    assert result.road_crossing_count == 1


def test_tangent_or_collinear_road_contact_is_not_a_crossing() -> None:
    tangent = make_feature("T", "road", LineString([(100, 0), (100, 20)]))
    collinear = make_feature("C", "road", LineString([(20, 0), (80, 0)]))

    result = analyse(features=(tangent, collinear))

    assert result.road_crossing_count == 0
    assert len(result.intersections) == 2


def test_polygon_road_passage_is_one_crossing() -> None:
    road = make_feature("R1", "road", Polygon([(45, -5), (55, -5), (55, 5), (45, 5)]))

    result = analyse(features=(road,))

    assert result.road_crossing_count == 1
    assert result.intersections[0].route_overlap_length_m == pytest.approx(10.0)


def test_route_along_polygon_road_boundary_is_not_a_crossing() -> None:
    route = make_route(((0, 5), (100, 5)))
    road = make_feature("R1", "road", Polygon([(45, -5), (55, -5), (55, 5), (45, 5)]))

    result = analyse(routes=(route,), features=(road,))

    assert result.road_crossing_count == 0
    assert len(result.intersections) == 1


def test_restricted_events_and_unique_features_are_separate_aggregates() -> None:
    routes = (
        make_route(end_node_id="B1"),
        make_route(
            ((0, 5), (100, 5)),
            start_node_id="A2",
            end_node_id="B2",
        ),
    )
    restricted = make_feature(
        "Z1",
        "restricted",
        Polygon([(20, -20), (40, -20), (40, 20), (20, 20)]),
        "hard",
    )

    result = analyse(routes=routes, features=(restricted,))

    assert result.restricted_intersection_count == 2
    assert result.unique_restricted_feature_count == 1
    assert result.has_hard_violation


def test_multipolygon_constraint_is_supported() -> None:
    feature = make_feature(
        "P1",
        "parcel",
        MultiPolygon(
            [
                Polygon([(10, -5), (20, -5), (20, 5), (10, 5)]),
                Polygon([(70, -5), (80, -5), (80, 5), (70, 5)]),
            ]
        ),
    )

    result = analyse(features=(feature,))

    assert result.intersections[0].intersection_area_m2 == pytest.approx(200.0)


def test_invalid_polygon_is_repaired_before_analysis() -> None:
    bowtie = Polygon([(20, -5), (40, 5), (20, 5), (40, -5), (20, -5)])
    assert not bowtie.is_valid

    result = analyse(features=(make_feature("P1", "parcel", bowtie),))

    assert len(result.intersections) == 1
    assert result.intersections[0].geometry.is_valid


def test_empty_noncritical_constraint_is_reported_as_skipped() -> None:
    result = analyse(features=(make_feature("P1", "parcel", Polygon()),))

    assert result.intersections == ()
    assert len(result.skipped_constraints) == 1
    assert result.skipped_constraints[0].feature_id == "P1"


def test_empty_hard_or_restricted_constraint_is_rejected() -> None:
    hard = make_feature("P1", "parcel", Polygon(), "hard")
    restricted = make_feature("Z1", "restricted", Polygon())

    with pytest.raises(ValueError, match="Critical constraint"):
        analyse(features=(hard,))
    with pytest.raises(ValueError, match="Critical constraint"):
        analyse(features=(restricted,))


def test_crs_mismatch_is_rejected() -> None:
    with pytest.raises(ValueError, match="do not match"):
        analyse(constraint_crs=CRS("EPSG:32633"))


def test_equivalent_crs_representations_are_accepted() -> None:
    equivalent = CRS.from_wkt(PROJECT_CRS.to_wkt())

    result = analyse(constraint_crs=equivalent)

    assert len(result.corridors) == 1


def test_geographic_or_non_metre_crs_is_rejected() -> None:
    geographic = CRS("EPSG:4326")
    feet = CRS("EPSG:2230")

    with pytest.raises(ValueError, match="projected CRS"):
        analyse(route_crs=geographic, constraint_crs=geographic)
    with pytest.raises(ValueError, match="measured in metres"):
        analyse(route_crs=feet, constraint_crs=feet)


@pytest.mark.parametrize(
    ("config", "message"),
    [
        (RowConfig(corridor_width_m=0.0), "greater than zero"),
        (RowConfig(corridor_width_m=-1.0), "greater than zero"),
        (RowConfig(corridor_width_m=math.nan), "must be finite"),
        (RowConfig(corridor_width_m=math.inf), "must be finite"),
        (
            RowConfig(corridor_width_m=10.0, minimum_overlap_area_m2=-1.0),
            "must be non-negative",
        ),
        (
            RowConfig(corridor_width_m=10.0, crossing_tolerance_m=-1.0),
            "must be non-negative",
        ),
    ],
)
def test_invalid_config_is_rejected(config: RowConfig, message: str) -> None:
    with pytest.raises(ValueError, match=message):
        analyse(config=config)


def test_unsupported_layer_severity_and_geometry_are_rejected() -> None:
    invalid_layer = make_feature("X", "building", Polygon([(0, 0), (1, 0), (1, 1)]))
    invalid_severity = make_feature(
        "P", "parcel", Polygon([(0, 0), (1, 0), (1, 1)]), "critical"
    )
    invalid_geometry = make_feature("P", "parcel", LineString([(0, 0), (1, 1)]))

    with pytest.raises(ValueError, match="unsupported layer type"):
        analyse(features=(invalid_layer,))
    with pytest.raises(ValueError, match="unsupported severity"):
        analyse(features=(invalid_severity,))
    with pytest.raises(ValueError, match="unsupported geometry type"):
        analyse(features=(invalid_geometry,))


def test_duplicate_constraint_identity_is_rejected() -> None:
    first = make_feature(
        "P1", "parcel", Polygon([(10, -5), (20, -5), (20, 5), (10, 5)])
    )
    second = make_feature(
        "P1", "parcel", Polygon([(30, -5), (40, -5), (40, 5), (30, 5)])
    )

    with pytest.raises(ValueError, match="Duplicate constraint identity"):
        analyse(features=(first, second))


def test_overlapping_corridors_report_summed_and_unique_area() -> None:
    routes = (
        make_route(end_node_id="B1"),
        make_route(
            ((0, 5), (100, 5)),
            start_node_id="A2",
            end_node_id="B2",
        ),
    )

    result = analyse(routes=routes)

    assert result.total_row_area_m2 == pytest.approx(
        sum(corridor.row_area_m2 for corridor in result.corridors)
    )
    assert result.unique_row_footprint_area_m2 < result.total_row_area_m2


def test_boundary_touch_is_reported_and_threshold_can_filter_it() -> None:
    touching = make_feature(
        "P1", "parcel", Polygon([(20, 10), (40, 10), (40, 20), (20, 20)])
    )

    included = analyse(features=(touching,))
    filtered = analyse(
        features=(touching,),
        config=RowConfig(
            corridor_width_m=20.0,
            minimum_overlap_area_m2=0.1,
            minimum_overlap_length_m=0.1,
        ),
    )

    assert included.intersections[0].touches_only
    assert filtered.intersections == ()


def test_multiple_feeder_route_identity_is_preserved_in_intersections() -> None:
    routes = (
        make_route(end_node_id="B1"),
        make_route(
            ((0, 5), (100, 5)),
            feeder_id="F2",
            start_node_id="C",
            end_node_id="D",
        ),
    )
    forest = make_feature(
        "FST", "forest", Polygon([(20, -20), (40, -20), (40, 20), (20, 20)])
    )

    result = analyse(routes=routes, features=(forest,))

    assert {
        (item.feeder_id, item.start_node_id, item.end_node_id)
        for item in result.intersections
    } == {("F1", "A", "B1"), ("F2", "C", "D")}


def test_duplicate_route_identity_is_rejected() -> None:
    route = make_route()

    with pytest.raises(ValueError, match="Duplicate refined route identity"):
        analyse(routes=(route, route))


def test_route_length_metadata_must_match_geometry() -> None:
    route = make_route(refined_length_m=99.0)

    with pytest.raises(ValueError, match="length metadata"):
        analyse(routes=(route,))


def test_analysis_is_deterministic() -> None:
    features = (
        make_feature("R", "road", LineString([(50, -20), (50, 20)])),
        make_feature("P", "parcel", Polygon([(10, -5), (20, -5), (20, 5), (10, 5)])),
    )

    first = analyse(features=features)
    second = analyse(features=features)

    assert first == second
