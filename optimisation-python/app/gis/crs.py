# Reference Journal: obsidian-vault/journal/2026-08-07.md
import pyproj
import shapely.ops
from shapely.geometry.base import BaseGeometry

WGS84_CRS = pyproj.CRS("EPSG:4326")


def get_utm_crs(lon: float, lat: float) -> pyproj.CRS:
    """
    Get the appropriate UTM CRS for a given longitude and latitude.
    This is necessary to transform WGS84 coordinates into metres for accurate
    distance calculations and optimisations.
    """
    utm_crs_list = pyproj.database.query_utm_crs_info(
        datum_name="WGS 84",
        area_of_interest=pyproj.aoi.AreaOfInterest(
            west_lon_degree=lon,
            south_lat_degree=lat,
            east_lon_degree=lon,
            north_lat_degree=lat,
        ),
    )
    if not utm_crs_list:
        raise ValueError(f"Could not find UTM CRS for lon={lon}, lat={lat}")
    return pyproj.CRS.from_epsg(utm_crs_list[0].code)


def get_transformer(src_crs: pyproj.CRS, dst_crs: pyproj.CRS) -> pyproj.Transformer:
    """
    Get a PyProj Transformer from src_crs to dst_crs.
    always_xy=True ensures coordinates are handled in (lon, lat) / (x, y) order,
    which is standard for Shapely and GeoJSON.
    """
    return pyproj.Transformer.from_crs(src_crs, dst_crs, always_xy=True)


def transform_geometry(
    geometry: BaseGeometry, transformer: pyproj.Transformer
) -> BaseGeometry:
    """
    Transform a Shapely geometry using the given transformer.
    """
    return shapely.ops.transform(transformer.transform, geometry)
