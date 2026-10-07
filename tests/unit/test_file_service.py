import pytest
from unittest.mock import MagicMock
from app.services.file_service import FileService
from app.models.file import FileRecord, FileProcessingStatus
from app.exceptions.file_exceptions import ResourceNotFoundException


def test_get_file_info_not_found():
    repo = MagicMock()
    repo.get_file_by_id.return_value = None

    service = FileService(
        repository=repo,
        geospatial_service=MagicMock(),
        crs_service=MagicMock(),
        measurement_service=MagicMock()
    )

    with pytest.raises(ResourceNotFoundException):
        service.get_file_info("nonexistent_id")


def test_get_file_info_success():
    repo = MagicMock()
    mock_record = FileRecord(
        id="abc-123",
        filename="test.kml",
        original_filename="test.kml",
        status=FileProcessingStatus.COMPLETED,
        source_crs="EPSG:4326",
        feature_count=5
    )
    repo.get_file_by_id.return_value = mock_record

    service = FileService(
        repository=repo,
        geospatial_service=MagicMock(),
        crs_service=MagicMock(),
        measurement_service=MagicMock()
    )

    detail = service.get_file_info("abc-123")
    assert detail.id == "abc-123"
    assert detail.status == FileProcessingStatus.COMPLETED
    assert detail.feature_count == 5
