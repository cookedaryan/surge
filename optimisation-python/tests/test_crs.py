from shapely.geometry import Point

from app.gis.crs import WGS84_CRS, get_transformer, get_utm_crs, transform_geometry


def test_get_utm_crs() -> None:
    # London approx (lon: 0.1, lat: 51.5) -> UTM zone 31N (EPSG:32631)
    crs = get_utm_crs(0.1, 51.5)
    assert crs.to_epsg() == 32631

    # New York approx (lon: -74.0, lat: 40.7) -> UTM zone 18N (EPSG:32618)
    crs = get_utm_crs(-74.0, 40.7)
    assert crs.to_epsg() == 32618

def test_transform_geometry() -> None:
    # Point in London
    pt_wgs = Point(0.1276, 51.5072)
    utm_crs = get_utm_crs(pt_wgs.x, pt_wgs.y)
    
    transformer = get_transformer(WGS84_CRS, utm_crs)
    pt_utm = transform_geometry(pt_wgs, transformer)
    
    # Check transformed coordinates are somewhat large (metres)
    assert pt_utm.x > 10000
    assert pt_utm.y > 10000

    # Transform back
    transformer_inv = get_transformer(utm_crs, WGS84_CRS)
    pt_inv = transform_geometry(pt_utm, transformer_inv)

    assert pt_inv.distance(pt_wgs) < 1e-6
