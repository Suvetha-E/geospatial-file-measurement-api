import pytest
from sqlalchemy.orm import Session
from app.models.file import FileRecord, MeasurementRecord, FileProcessingStatus
from app.repositories.file_repository import FileRepository


def test_file_repository_crud(db_session: Session):
    repo = FileRepository(db_session)

    # 1. Create File Record
    file_record = FileRecord(
        id="test-uuid-1",
        filename="survey.kml",
        original_filename="original_survey.kml",
        status=FileProcessingStatus.UPLOADED,
        source_crs="EPSG:4326",
        feature_count=0
    )
    created = repo.create_file(file_record)
    assert created.id == "test-uuid-1"
    assert created.status == FileProcessingStatus.UPLOADED

    # 2. Get File Record
    fetched = repo.get_file_by_id("test-uuid-1")
    assert fetched is not None
    assert fetched.filename == "survey.kml"

    # 3. Update File Status
    updated = repo.update_file_status("test-uuid-1", FileProcessingStatus.COMPLETED, feature_count=2)
    assert updated.status == FileProcessingStatus.COMPLETED
    assert updated.feature_count == 2

    # 4. Save Measurements
    m1 = MeasurementRecord(
        file_id="test-uuid-1",
        feature_id=0,
        geometry_type="Polygon",
        properties={"name": "Parcel A"},
        measurement_type="area",
        measurement_value=15000.50,
        measurement_unit="m2",
        processing_status="SUCCESS"
    )
    m2 = MeasurementRecord(
        file_id="test-uuid-1",
        feature_id=1,
        geometry_type="LineString",
        properties={"name": "Road"},
        measurement_type="length",
        measurement_value=450.25,
        measurement_unit="m",
        processing_status="SUCCESS"
    )
    repo.save_measurements([m1, m2])

    # 5. Retrieve Measurements
    measurements = repo.get_measurements_by_file_id("test-uuid-1")
    assert len(measurements) == 2
    assert measurements[0].feature_id == 0
    assert measurements[0].measurement_value == 15000.50
    assert measurements[1].feature_id == 1
    assert measurements[1].measurement_value == 450.25
