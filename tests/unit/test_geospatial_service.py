import pytest
from pathlib import Path
from app.services.geospatial_service import GeospatialService
from app.exceptions.file_exceptions import InvalidFileException


def test_read_kml_features(tmp_path: Path, sample_kml_bytes: bytes):
    kml_file = tmp_path / "test.kml"
    kml_file.write_bytes(sample_kml_bytes)

    service = GeospatialService()
    features, source_crs = service.read_file_features(kml_file, ".kml")

    assert source_crs == "EPSG:4326"
    assert len(features) == 3

    # Feature 0: Polygon
    assert features[0]["feature_id"] == 0
    assert features[0]["geometry_type"] == "Polygon"
    assert features[0]["properties"].get("name") == "Zone Alpha Polygon"

    # Feature 1: LineString
    assert features[1]["feature_id"] == 1
    assert features[1]["geometry_type"] == "LineString"

    # Feature 2: Point
    assert features[2]["feature_id"] == 2
    assert features[2]["geometry_type"] == "Point"


def test_read_corrupted_kml(tmp_path: Path, corrupted_kml_bytes: bytes):
    kml_file = tmp_path / "corrupted.kml"
    kml_file.write_bytes(corrupted_kml_bytes)

    service = GeospatialService()
    with pytest.raises(InvalidFileException):
        service.read_file_features(kml_file, ".kml")
