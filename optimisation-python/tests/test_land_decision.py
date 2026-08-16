import datetime

from pyproj import CRS
from shapely.geometry import Point, Polygon

from app.algorithms.pole_micro_siting import PoleMicroSitingContext, _is_feasible
from app.algorithms.pole_placement import (
    CollectorPoleResult,
    PhysicalPole,
    Pole,
    PolePlacementConfig,
)
from app.gis.constraints import ConstraintLayer, ConstraintMode, ConstraintType
from app.land.decision import assess_candidate_land
from app.land.models import (
    LandAvailabilityStatus,
    LandCommercialContext,
    ParcelCommercialProfile,
)

PROJECTED_CRS = CRS.from_epsg(3857)


def _parcel_layer(parcel_id: str) -> ConstraintLayer:
    return ConstraintLayer(
        layer_id=parcel_id,
        layer_type=ConstraintType.PARCEL,
        mode=ConstraintMode.SOFT_PENALTY,
        geometry=Polygon([(40, -10), (60, -10), (60, 10), (40, 10)]),
        buffer_m=0.0,
        cost_weight=1.0,
        crs=PROJECTED_CRS,
    )


def _land_context() -> LandCommercialContext:
    return LandCommercialContext(
        currency="USD",
        as_of_date=datetime.date(2026, 1, 1),
        parcel_profiles=(
            ParcelCommercialProfile(
                parcel_id="AVAILABLE",
                owner_id="OWNER-A",
                availability_status=LandAvailabilityStatus.AVAILABLE,
                transaction_options=(),
            ),
            ParcelCommercialProfile(
                parcel_id="UNAVAILABLE",
                owner_id="OWNER-B",
                availability_status=LandAvailabilityStatus.UNAVAILABLE,
                transaction_options=(),
            ),
        ),
    )


def test_pole_assessment_includes_all_overlapping_parcels() -> None:
    pole_result = CollectorPoleResult(
        routes=(),
        total_poles=1,
        total_spans=0,
        physical_poles=(
            PhysicalPole(
                pole_id="P1",
                geometry=Point(50, 0),
                pole_type="intermediate",
                feeder_ids=("F1",),
                route_ids=("R1",),
                source_pole_ids=("P1",),
                topology_node_id=None,
            ),
        ),
    )

    assessment = assess_candidate_land(
        scenario_id="SCN-1",
        poles=pole_result,
        land_context=_land_context(),
        constraint_layers=(
            _parcel_layer("AVAILABLE"),
            _parcel_layer("UNAVAILABLE"),
        ),
    )

    assert assessment.parcel_count == 2
    assert assessment.owner_interaction_count == 2
    assert assessment.unavailable_parcel_ids == ("UNAVAILABLE",)
    assert not assessment.is_feasible


def test_micro_siting_rejects_any_overlapping_unavailable_parcel() -> None:
    pole_config = PolePlacementConfig(
        target_span_m=50.0,
        min_span_m=10.0,
        max_span_m=100.0,
    )
    context = PoleMicroSitingContext(
        route_geometries={},
        route_owner_ids=frozenset(),
        constraint_layers=(
            _parcel_layer("AVAILABLE"),
            _parcel_layer("UNAVAILABLE"),
        ),
        land_context=_land_context(),
        pole_config=pole_config,
    )
    previous = Pole("P0", "F1", 0, Point(0, 0), "terminal", 0.0)
    following = Pole("P2", "F1", 2, Point(100, 0), "terminal", 100.0)

    assert not _is_feasible(
        Point(50, 0),
        50.0,
        previous,
        following,
        context,
        pole_config.max_span_m,
    )
