from fastapi import Depends
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.repositories.file_repository import FileRepository
from app.services.geospatial_service import GeospatialService
from app.services.crs_service import CRSService
from app.services.measurement_service import MeasurementService
from app.services.file_service import FileService


def get_file_repository(db: Session = Depends(get_db)) -> FileRepository:
    return FileRepository(db)


def get_geospatial_service() -> GeospatialService:
    return GeospatialService()


def get_crs_service() -> CRSService:
    return CRSService()


def get_measurement_service() -> MeasurementService:
    return MeasurementService()


def get_file_service(
    repo: FileRepository = Depends(get_file_repository),
    geospatial_service: GeospatialService = Depends(get_geospatial_service),
    crs_service: CRSService = Depends(get_crs_service),
    measurement_service: MeasurementService = Depends(get_measurement_service),
) -> FileService:
    return FileService(
        repository=repo,
        geospatial_service=geospatial_service,
        crs_service=crs_service,
        measurement_service=measurement_service,
    )
