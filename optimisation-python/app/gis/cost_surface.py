import math
from dataclasses import dataclass

import numpy as np
from affine import Affine
from pyproj import CRS

from app.models.spatial import ProjectSpatialData


@dataclass(frozen=True)
class CostSurface:
    costs: np.ndarray
    transform: Affine
    crs: CRS
    width: int
    height: int
    resolution_m: float


def world_to_grid(x: float, y: float, surface: CostSurface) -> tuple[int, int]:
    """
    Convert geographic (projected) coordinates (x, y) to grid cell indices (row, col).
    """
    col, row = ~surface.transform * (x, y)
    return int(math.floor(row)), int(math.floor(col))


def grid_to_world(row: int, col: int, surface: CostSurface) -> tuple[float, float]:
    """
    Convert grid cell indices (row, col) to the centre of the cell in world coordinates.
    """
    x, y = surface.transform * (col + 0.5, row + 0.5)
    return float(x), float(y)


def build_project_cost_surface(
    project: ProjectSpatialData,
    resolution_m: float = 10.0,
    padding_m: float = 100.0,
    *,
    max_cells: int | None = None,
) -> CostSurface:
    """
    Creates a CostSurface covering the full project extent (WTGs + Substation).
    """
    if not math.isfinite(resolution_m) or resolution_m <= 0:
        raise ValueError("Resolution must be a positive finite number.")
    if max_cells is not None and (
        not isinstance(max_cells, int) or isinstance(max_cells, bool) or max_cells < 1
    ):
        raise ValueError("max_cells must be a positive integer when provided.")

    points = [wtg.location for wtg in project.turbines]
    points.append(project.substation.location)

    if not points:
        raise ValueError("Cannot build cost surface for empty project.")

    min_x = min(p.x for p in points)
    max_x = max(p.x for p in points)
    min_y = min(p.y for p in points)
    max_y = max(p.y for p in points)

    # Add padding
    min_x -= padding_m
    max_x += padding_m
    min_y -= padding_m
    max_y += padding_m

    width = int(math.ceil((max_x - min_x) / resolution_m))
    height = int(math.ceil((max_y - min_y) / resolution_m))

    width = max(1, width)
    height = max(1, height)

    total_cells = width * height
    if max_cells is not None and total_cells > max_cells:
        raise ValueError(
            "Cost surface exceeds maximum allowed cells "
            f"({total_cells} > {max_cells}). Reduce padding or increase resolution."
        )

    # Affine transform for Raster (origin top-left, y points down)
    transform = Affine.translation(min_x, max_y) * Affine.scale(
        resolution_m, -resolution_m
    )

    # Allocate only after validating the complete raster dimensions.
    costs = np.ones((height, width), dtype=np.float32)

    return CostSurface(
        costs=costs,
        transform=transform,
        crs=project.projected_crs,
        width=width,
        height=height,
        resolution_m=resolution_m,
    )
