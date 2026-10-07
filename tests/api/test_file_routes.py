import io
import pytest
from fastapi.testclient import TestClient


def test_upload_kml_success(client: TestClient, sample_kml_bytes: bytes):
    files = {"file": ("london_survey.kml", io.BytesIO(sample_kml_bytes), "application/vnd.google-earth.kml+xml")}
    response = client.post("/api/files/", files=files)

    assert response.status_code == 201
    data = response.json()
    assert "id" in data
    assert data["filename"].endswith(".kml")
    assert data["feature_count"] == 3
    assert data["crs"] == "EPSG:4326"
    assert data["status"] == "COMPLETED"

    file_id = data["id"]

    # Retrieve file info
    info_resp = client.get(f"/api/files/{file_id}/")
    assert info_resp.status_code == 200
    info_data = info_resp.json()
    assert info_data["id"] == file_id
    assert info_data["feature_count"] == 3

    # Retrieve measurements
    meas_resp = client.get(f"/api/files/{file_id}/measurements/")
    assert meas_resp.status_code == 200
    meas_data = meas_resp.json()
    assert meas_data["file_id"] == file_id
    assert len(meas_data["measurements"]) == 3

    # Feature 0: Polygon -> area measurement in m2
    f0 = meas_data["measurements"][0]
    assert f0["feature_id"] == 0
    assert f0["geometry_type"] == "Polygon"
    assert f0["measurement_type"] == "area"
    assert f0["measurement_unit"] == "m2"
    assert f0["measurement_value"] > 500000.0

    # Feature 1: LineString -> length measurement in m
    f1 = meas_data["measurements"][1]
    assert f1["feature_id"] == 1
    assert f1["geometry_type"] == "LineString"
    assert f1["measurement_type"] == "length"
    assert f1["measurement_unit"] == "m"
    assert f1["measurement_value"] > 1000.0

    # Feature 2: Point -> no measurement
    f2 = meas_data["measurements"][2]
    assert f2["feature_id"] == 2
    assert f2["geometry_type"] == "Point"
    assert f2["measurement_type"] is None
    assert f2["measurement_value"] is None


def test_upload_shapefile_zip_success(client: TestClient, sample_shapefile_zip_bytes: bytes):
    files = {"file": ("parcels.zip", io.BytesIO(sample_shapefile_zip_bytes), "application/zip")}
    response = client.post("/api/files/", files=files)

    assert response.status_code == 201
    data = response.json()
    assert "id" in data
    assert data["feature_count"] == 2
    assert data["status"] == "COMPLETED"

    file_id = data["id"]

    # Verify measurements
    meas_resp = client.get(f"/api/files/{file_id}/measurements/")
    assert meas_resp.status_code == 200
    meas_data = meas_resp.json()
    assert len(meas_data["measurements"]) == 2
    for m in meas_data["measurements"]:
        assert m["geometry_type"] == "Polygon"
        assert m["measurement_type"] == "area"
        assert m["measurement_unit"] == "m2"


def test_upload_unsupported_file_extension(client: TestClient):
    files = {"file": ("document.pdf", io.BytesIO(b"dummy pdf content"), "application/pdf")}
    response = client.post("/api/files/", files=files)

    assert response.status_code == 400
    data = response.json()
    assert "error" in data
    assert data["error"]["code"] == "UNSUPPORTED_FILE_TYPE"


def test_upload_invalid_zip(client: TestClient, invalid_zip_bytes: bytes):
    files = {"file": ("corrupted.zip", io.BytesIO(invalid_zip_bytes), "application/zip")}
    response = client.post("/api/files/", files=files)

    assert response.status_code == 400
    data = response.json()
    assert "error" in data
    assert data["error"]["code"] == "INVALID_ZIP"


def test_upload_zip_without_shp(client: TestClient, zip_without_shp_bytes: bytes):
    files = {"file": ("noshp.zip", io.BytesIO(zip_without_shp_bytes), "application/zip")}
    response = client.post("/api/files/", files=files)

    assert response.status_code == 400
    data = response.json()
    assert "error" in data
    assert data["error"]["code"] == "SHAPEFILE_NOT_FOUND"


def test_upload_corrupted_kml(client: TestClient, corrupted_kml_bytes: bytes):
    files = {"file": ("corrupted.kml", io.BytesIO(corrupted_kml_bytes), "application/vnd.google-earth.kml+xml")}
    response = client.post("/api/files/", files=files)

    assert response.status_code == 400
    data = response.json()
    assert "error" in data
    assert data["error"]["code"] == "INVALID_FILE"


def test_get_nonexistent_file_404(client: TestClient):
    response = client.get("/api/files/nonexistent-id-9999/")
    assert response.status_code == 404
    data = response.json()
    assert "error" in data
    assert data["error"]["code"] == "RESOURCE_NOT_FOUND"


def test_get_nonexistent_measurements_404(client: TestClient):
    response = client.get("/api/files/nonexistent-id-9999/measurements/")
    assert response.status_code == 404
    data = response.json()
    assert "error" in data
    assert data["error"]["code"] == "RESOURCE_NOT_FOUND"


def test_upload_shapefile_missing_prj_fails(client: TestClient, shapefile_zip_without_prj_bytes: bytes):
    files = {"file": ("noprj.zip", io.BytesIO(shapefile_zip_without_prj_bytes), "application/zip")}
    response = client.post("/api/files/", files=files)

    assert response.status_code == 400
    data = response.json()
    assert "error" in data
    assert data["error"]["code"] == "MISSING_CRS"


def test_upload_empty_kml_fails(client: TestClient):
    files = {"file": ("empty.kml", io.BytesIO(b""), "application/vnd.google-earth.kml+xml")}
    response = client.post("/api/files/", files=files)

    assert response.status_code == 400
    data = response.json()
    assert "error" in data
    assert data["error"]["code"] == "INVALID_FILE"


def test_upload_empty_zip_fails(client: TestClient):
    files = {"file": ("empty.zip", io.BytesIO(b""), "application/zip")}
    response = client.post("/api/files/", files=files)

    assert response.status_code == 400
    data = response.json()
    assert "error" in data
    assert data["error"]["code"] == "INVALID_FILE"


def test_upload_path_traversal_zip_rejected(client: TestClient, path_traversal_zip_bytes: bytes):
    files = {"file": ("traversal.zip", io.BytesIO(path_traversal_zip_bytes), "application/zip")}
    response = client.post("/api/files/", files=files)

    assert response.status_code == 400
    data = response.json()
    assert "error" in data
    assert data["error"]["code"] == "INVALID_ZIP"


def test_upload_exceeds_max_size_rejected(client: TestClient, monkeypatch):
    from app.core.config import settings
    monkeypatch.setattr(settings, "MAX_UPLOAD_SIZE", 50)

    large_payload = b"X" * 200
    files = {"file": ("large.kml", io.BytesIO(large_payload), "application/vnd.google-earth.kml+xml")}
    response = client.post("/api/files/", files=files)

    assert response.status_code == 400
    data = response.json()
    assert "error" in data
    assert data["error"]["code"] == "INVALID_FILE"


def test_typing_get_type_hints_crs_service():
    import typing
    from app.services.crs_service import CRSService
    hints = typing.get_type_hints(CRSService.parse_crs)
    assert "crs_input" in hints

