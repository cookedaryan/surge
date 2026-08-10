# Reference Journal: obsidian-vault/journal/2026-08-07.md
from dataclasses import dataclass

from pyproj import CRS
from shapely.geometry import Point


@dataclass(frozen=True)
class WindTurbine:
    turbine_id: str
    location: Point
    capacity_mw: float | None = None


@dataclass(frozen=True)
class Substation:
    substation_id: str
    location: Point
    capacity_mw: float | None = None


@dataclass(frozen=True)
class ProjectSpatialData:
    turbines: tuple[WindTurbine, ...]
    substation: Substation
    projected_crs: CRS
