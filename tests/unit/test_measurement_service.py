import pytest
from shapely.geometry import Polygon, LineString, Point, GeometryCollection
from app.services.measurement_service import MeasurementService


def test_polygon_area_calculation():
    service = MeasurementService()
    # 100m x 100m square polygon in projected coordinates
    poly = Polygon([(0, 0), (0, 100), (100, 100), (100, 0), (0, 0)])
    m_type, m_val, m_unit, status, err = service.calculate_measurement(poly, "Polygon")

    assert status == "SUCCESS"
    assert err is None
    assert m_type == "area"
    assert m_unit == "m2"
    assert pytest.approx(m_val, 0.01) == 10000.0


def test_linestring_length_calculation():
    service = MeasurementService()
    # 150m line in projected coordinates
    line = LineString([(0, 0), (100, 0), (100, 50)])
    m_type, m_val, m_unit, status, err = service.calculate_measurement(line, "LineString")

    assert status == "SUCCESS"
    assert err is None
    assert m_type == "length"
    assert m_unit == "m"
    assert pytest.approx(m_val, 0.01) == 150.0


def test_point_measurement():
    service = MeasurementService()
    pt = Point(50, 50)
    m_type, m_val, m_unit, status, err = service.calculate_measurement(pt, "Point")

    assert status == "SUCCESS"
    assert err is None
    assert m_type is None
    assert m_val is None
    assert m_unit is None


def test_unsupported_geometry():
    service = MeasurementService()
    gc = GeometryCollection([Point(0, 0), LineString([(0, 0), (1, 1)])])
    m_type, m_val, m_unit, status, err = service.calculate_measurement(gc, "GeometryCollection")

    assert status == "SKIPPED"
    assert "not supported" in err.lower()
    assert m_val is None


def test_empty_geometry():
    service = MeasurementService()
    poly = Polygon()
    m_type, m_val, m_unit, status, err = service.calculate_measurement(poly, "Polygon")

    assert status == "ERROR"
    assert "empty" in err.lower()
    assert m_val is None
