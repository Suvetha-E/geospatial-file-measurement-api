import uuid
from pathlib import Path
from typing import Optional, List
from fastapi import UploadFile

from app.core.config import settings
from app.core.logging import logger
from app.models.file import FileRecord, MeasurementRecord, FileProcessingStatus
from app.repositories.file_repository import FileRepository
from app.services.geospatial_service import GeospatialService
from app.services.crs_service import CRSService
from app.services.measurement_service import MeasurementService
from app.utils.file_utils import (
    validate_upload_file,
    generate_unique_filename,
    extract_zip_safely,
    cleanup_directory,
)
from app.utils.geometry_utils import get_geometry_centroid_coords
from app.exceptions.base import AppException
from app.exceptions.file_exceptions import (
    FileProcessingException,
    ResourceNotFoundException,
    InvalidFileException
)
from app.schemas.file import FileUploadResponse, FileDetailResponse
from app.schemas.measurement import FileMeasurementsResponse, MeasurementItem


class FileService:
    """Service orchestrating file upload validation, geospatial parsing, measurement, and persistence."""

    def __init__(
        self,
        repository: FileRepository,
        geospatial_service: GeospatialService,
        crs_service: CRSService,
        measurement_service: MeasurementService,
    ):
        self.repository = repository
        self.geospatial_service = geospatial_service
        self.crs_service = crs_service
        self.measurement_service = measurement_service

    async def process_file(self, file: UploadFile) -> FileUploadResponse:
        """Processes an uploaded geospatial file end-to-end."""
        # 1. Validate file
        validate_upload_file(file)

        # 2. Save uploaded file to upload directory
        file_id = str(uuid.uuid4())
        original_filename = file.filename or "uploaded_file"
        ext = Path(original_filename).suffix.lower()
        unique_filename = f"{file_id}{ext}"
        saved_file_path = settings.UPLOAD_DIRECTORY / unique_filename

        total_bytes = 0
        chunk_size = 1024 * 1024  # 1 MB chunk

        try:
            with open(saved_file_path, "wb") as f:
                while True:
                    chunk = await file.read(chunk_size)
                    if not chunk:
                        break
                    total_bytes += len(chunk)
                    if total_bytes > settings.MAX_UPLOAD_SIZE:
                        f.close()
                        if saved_file_path.exists():
                            saved_file_path.unlink()
                        raise InvalidFileException("File size exceeds maximum allowed limit.")
                    f.write(chunk)

            if total_bytes == 0:
                if saved_file_path.exists():
                    saved_file_path.unlink()
                raise InvalidFileException("The uploaded file is empty.")
        except FileProcessingException:
            if saved_file_path.exists():
                try:
                    saved_file_path.unlink()
                except Exception:
                    pass
            raise
        except Exception as e:
            if saved_file_path.exists():
                try:
                    saved_file_path.unlink()
                except Exception:
                    pass
            logger.error(f"Error saving uploaded file: {e}")
            raise InvalidFileException(f"Could not save uploaded file: {str(e)}")

        # 3. Create initial database record
        file_record = FileRecord(
            id=file_id,
            filename=unique_filename,
            original_filename=original_filename,
            status=FileProcessingStatus.UPLOADED,
            source_crs=None,
            feature_count=0
        )
        self.repository.create_file(file_record)

        # 4. Temporary processing setup
        temp_dir: Optional[Path] = None

        try:
            # Update status to PROCESSING
            self.repository.update_file_status(file_id, FileProcessingStatus.PROCESSING)

            target_parse_path = saved_file_path
            parse_ext = ext

            if ext == ".zip":
                temp_dir = settings.TEMP_DIRECTORY / file_id
                temp_dir.mkdir(parents=True, exist_ok=True)
                target_parse_path = extract_zip_safely(saved_file_path, temp_dir)
                parse_ext = ".shp"

            # 5. Extract features & source CRS
            features, source_crs_str = self.geospatial_service.read_file_features(target_parse_path, parse_ext)
            source_crs = self.crs_service.parse_crs(source_crs_str)

            measurement_records: List[MeasurementRecord] = []

            # 6. Process each feature
            for feature in features:
                feature_id = feature["feature_id"]
                geom_type = feature["geometry_type"]
                raw_geom = feature["geometry"]
                props = feature.get("properties", {})

                measurement_type = None
                measurement_value = None
                measurement_unit = None
                proc_status = "SUCCESS"
                err_msg = None

                if raw_geom is not None and not raw_geom.is_empty:
                    try:
                        # Determine centroid for UTM projection
                        lon, lat = get_geometry_centroid_coords(raw_geom)
                        target_crs = self.crs_service.get_projected_crs(source_crs, lon, lat)

                        # Transform geometry to projected CRS
                        projected_geom = self.crs_service.transform_geometry(raw_geom, source_crs, target_crs)

                        # Calculate metric measurement
                        (
                            measurement_type,
                            measurement_value,
                            measurement_unit,
                            proc_status,
                            err_msg,
                        ) = self.measurement_service.calculate_measurement(projected_geom, geom_type)

                    except Exception as ex:
                        logger.warning(f"Error processing feature {feature_id}: {ex}")
                        proc_status = "ERROR"
                        err_msg = f"Geometry transformation error: {str(ex)}"
                else:
                    proc_status = "ERROR"
                    err_msg = "Null or empty geometry"

                record = MeasurementRecord(
                    file_id=file_id,
                    feature_id=feature_id,
                    geometry_type=geom_type,
                    properties=props,
                    measurement_type=measurement_type,
                    measurement_value=measurement_value,
                    measurement_unit=measurement_unit,
                    processing_status=proc_status,
                    error_message=err_msg
                )
                measurement_records.append(record)

            # 7. Persist measurement records
            self.repository.save_measurements(measurement_records)

            # 8. Update file record to COMPLETED
            updated_record = self.repository.update_file_status(
                file_id=file_id,
                status=FileProcessingStatus.COMPLETED,
                source_crs=source_crs_str,
                feature_count=len(features)
            )

            return FileUploadResponse.model_validate(updated_record)

        except Exception as e:
            logger.error(f"File processing failed for {file_id}: {e}", exc_info=True)
            self.repository.update_file_status(file_id, FileProcessingStatus.FAILED)
            if isinstance(e, (FileProcessingException, AppException)):
                raise e
            raise FileProcessingException(f"Processing failed: {str(e)}")

        finally:
            if temp_dir:
                cleanup_directory(temp_dir)

    def get_file_info(self, file_id: str) -> FileDetailResponse:
        """Retrieves file details by ID."""
        file_record = self.repository.get_file_by_id(file_id)
        if not file_record:
            raise ResourceNotFoundException(f"File with ID '{file_id}' not found.")
        return FileDetailResponse.model_validate(file_record)

    def get_file_measurements(self, file_id: str) -> FileMeasurementsResponse:
        """Retrieves all measurement records for a given file ID."""
        file_record = self.repository.get_file_by_id(file_id)
        if not file_record:
            raise ResourceNotFoundException(f"File with ID '{file_id}' not found.")

        measurements = self.repository.get_measurements_by_file_id(file_id)
        item_schemas = [MeasurementItem.model_validate(m) for m in measurements]

        return FileMeasurementsResponse(
            file_id=file_id,
            measurements=item_schemas
        )
