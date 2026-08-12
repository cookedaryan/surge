import numpy as np
from affine import Affine
from pyproj import CRS
from shapely.geometry import Point

from app.gis.cost_surface import CostSurface
from app.models.spatial import ProjectSpatialData, Substation, WindTurbine


def build_demo_project_data() -> ProjectSpatialData:
    crs = CRS.from_epsg(32630)
    turbines = [
        WindTurbine("T01", Point(50.0, 700.0), 5.0),
        WindTurbine("T02", Point(100.0, 720.0), 5.0),
        WindTurbine("T03", Point(80.0, 660.0), 5.0),
        WindTurbine("T04", Point(150.0, 710.0), 5.0),
        WindTurbine("T05", Point(500.0, 700.0), 5.0),
        WindTurbine("T06", Point(550.0, 720.0), 5.0),
        WindTurbine("T07", Point(520.0, 660.0), 5.0),
        WindTurbine("T08", Point(580.0, 710.0), 5.0),
    ]
    substation = Substation("SUB1", Point(300.0, 100.0))
    return ProjectSpatialData(
        turbines=tuple(turbines),
        substation=substation,
        projected_crs=crs,
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
