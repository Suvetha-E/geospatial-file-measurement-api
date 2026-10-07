from typing import Optional, List
from sqlalchemy.orm import Session
from sqlalchemy import select
from app.models.file import FileRecord, MeasurementRecord, FileProcessingStatus


class FileRepository:
    def __init__(self, db: Session):
        self.db = db

    def create_file(self, file_record: FileRecord) -> FileRecord:
        """Persists a new file record."""
        self.db.add(file_record)
        self.db.commit()
        self.db.refresh(file_record)
        return file_record

    def get_file_by_id(self, file_id: str) -> Optional[FileRecord]:
        """Retrieves a file record by its ID."""
        stmt = select(FileRecord).where(FileRecord.id == file_id)
        return self.db.execute(stmt).scalar_one_or_none()

    def update_file_status(
        self,
        file_id: str,
        status: FileProcessingStatus,
        source_crs: Optional[str] = None,
        feature_count: Optional[int] = None
    ) -> Optional[FileRecord]:
        """Updates file processing status and optional metadata."""
        file_record = self.get_file_by_id(file_id)
        if not file_record:
            return None
        
        file_record.status = status
        if source_crs is not None:
            file_record.source_crs = source_crs
        if feature_count is not None:
            file_record.feature_count = feature_count

        self.db.commit()
        self.db.refresh(file_record)
        return file_record

    def save_measurements(self, measurements: List[MeasurementRecord]) -> List[MeasurementRecord]:
        """Persists a collection of measurement records."""
        self.db.add_all(measurements)
        self.db.commit()
        return measurements

    def get_measurements_by_file_id(self, file_id: str) -> List[MeasurementRecord]:
        """Retrieves all measurements associated with a file ID."""
        stmt = (
            select(MeasurementRecord)
            .where(MeasurementRecord.file_id == file_id)
            .order_by(MeasurementRecord.feature_id)
        )
        return list(self.db.execute(stmt).scalars().all())
