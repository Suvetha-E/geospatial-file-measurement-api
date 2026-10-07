import pytest
from pyproj import CRS
from shapely.geometry import Polygon
from app.services.crs_service import CRSService


def test_parse_crs_geographic():
    crs = CRSService.parse_crs("EPSG:4326")
    assert crs.is_geographic is True
    assert crs.to_epsg() == 4326


def test_parse_crs_invalid_fallback():
    crs = CRSService.parse_crs("INVALID_EPSG_999999")
    assert crs.is_geographic is True
    assert crs.to_epsg() == 4326


def test_determine_utm_crs():
    # London centroid (~ -0.12, 51.50) -> UTM Zone 30N (EPSG:32630)
    utm_crs = CRSService.determine_utm_crs(-0.12, 51.50)
    assert utm_crs.is_projected is True
    assert utm_crs.to_epsg() == 32630

    # Sydney centroid (~ 151.20, -33.86) -> UTM Zone 56S (EPSG:32756)
    utm_crs_syd = CRSService.determine_utm_crs(151.20, -33.86)
    assert utm_crs_syd.is_projected is True
    assert utm_crs_syd.to_epsg() == 32756


def test_get_projected_crs_from_geographic():
    service = CRSService()
    source_crs = service.parse_crs("EPSG:4326")
    target_crs = service.get_projected_crs(source_crs, -0.12, 51.50)

    assert target_crs.is_projected is True
    assert target_crs.to_epsg() == 32630


def test_transform_geometry_preserves_metric_scale():
    service = CRSService()
    source_crs = service.parse_crs("EPSG:4326")
    target_crs = service.determine_utm_crs(-0.12, 51.50)

    # 0.01 deg x 0.01 deg polygon in London
    poly = Polygon([
        (-0.12, 51.50),
        (-0.12, 51.51),
        (-0.11, 51.51),
        (-0.11, 51.50),
        (-0.12, 51.50)
    ])

    # Raw degree area is ~ 0.0001 square degrees (meaningless in metric)
    assert poly.area < 0.001

    transformed_poly = service.transform_geometry(poly, source_crs, target_crs)

    # Metric area in UTM projected meters should be approximately ~ 770,000 m2
    assert transformed_poly.area > 500000.0
