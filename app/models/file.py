import enum
from datetime import datetime, timezone
from typing import List, Optional, Any
from sqlalchemy import String, Integer, Float, DateTime, ForeignKey, Text, JSON, Enum as SQLEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.core.database import Base


class FileProcessingStatus(str, enum.Enum):
    UPLOADED = "UPLOADED"
    PROCESSING = "PROCESSING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class FileRecord(Base):
    __tablename__ = "files"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    filename: Mapped[str] = mapped_column(String(255), nullable=False)
    original_filename: Mapped[str] = mapped_column(String(255), nullable=False)
    status: Mapped[FileProcessingStatus] = mapped_column(
        SQLEnum(FileProcessingStatus),
        default=FileProcessingStatus.UPLOADED,
        nullable=False
    )
    source_crs: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    feature_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now, onupdate=utc_now, nullable=False)

    measurements: Mapped[List["MeasurementRecord"]] = relationship(
        "MeasurementRecord",
        back_populates="file",
        cascade="all, delete-orphan",
        order_by="MeasurementRecord.feature_id"
    )

    def __init__(self, **kw):
        if "created_at" not in kw:
            kw["created_at"] = utc_now()
        if "updated_at" not in kw:
            kw["updated_at"] = utc_now()
        super().__init__(**kw)

    @property
    def crs(self) -> Optional[str]:
        return self.source_crs


class MeasurementRecord(Base):
    __tablename__ = "measurements"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    file_id: Mapped[str] = mapped_column(String(36), ForeignKey("files.id", ondelete="CASCADE"), nullable=False, index=True)
    feature_id: Mapped[int] = mapped_column(Integer, nullable=False)
    geometry_type: Mapped[str] = mapped_column(String(50), nullable=False)
    properties: Mapped[Optional[Any]] = mapped_column(JSON, nullable=True)
    measurement_type: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    measurement_value: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    measurement_unit: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    processing_status: Mapped[str] = mapped_column(String(50), default="SUCCESS", nullable=False)
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    file: Mapped["FileRecord"] = relationship("FileRecord", back_populates="measurements")
