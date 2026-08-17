import numpy as np
from affine import Affine
from pyproj import CRS
from shapely.geometry import Point

from app.gis.cost_surface import CostSurface
from app.models.spatial import ProjectSpatialData, Substation, WindTurbine


def build_project_data(
    turbine_coordinates: tuple[tuple[float, float], ...],
    substation_coordinate: tuple[float, float],
    *,
    turbine_capacity_mw: float = 5.0,
    crs: CRS | None = None,
) -> ProjectSpatialData:
    """Construct spatial project data from canonical coordinate tuples."""
    project_crs = crs or CRS.from_epsg(32630)
    turbines = tuple(
        WindTurbine(
            turbine_id=f"T{index:02d}",
            location=Point(x, y),
            capacity_mw=turbine_capacity_mw,
        )
        for index, (x, y) in enumerate(turbine_coordinates, start=1)
    )
    return ProjectSpatialData(
        turbines=turbines,
        substation=Substation("SUB1", Point(*substation_coordinate)),
        projected_crs=project_crs,
    )


def build_demo_project_data() -> ProjectSpatialData:
    return build_project_data(
        (
            (50.0, 700.0),
            (100.0, 720.0),
            (80.0, 660.0),
            (150.0, 710.0),
            (500.0, 700.0),
            (550.0, 720.0),
            (520.0, 660.0),
            (580.0, 710.0),
        ),
        (300.0, 100.0),
    )


def build_demo_cost_surface() -> CostSurface:
    crs = CRS.from_epsg(32630)
    width = 80
    height = 80
    transform = Affine(10.0, 0.0, 0.0, 0.0, -10.0, 800.0)
    costs = np.ones((height, width), dtype=np.float32)
    return CostSurface(
        costs=costs,
        transform=transform,
        crs=crs,
        width=width,
        height=height,
        resolution_m=10.0,
    )
