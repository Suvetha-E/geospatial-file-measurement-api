from fastapi import APIRouter, Depends, UploadFile, File, status
from app.schemas.file import FileUploadResponse, FileDetailResponse
from app.schemas.measurement import FileMeasurementsResponse
from app.schemas.error import ErrorResponse
from app.services.file_service import FileService
from app.api.dependencies import get_file_service

router = APIRouter(prefix="/api/files", tags=["Geospatial Files"])


@router.post(
    "/",
    response_model=FileUploadResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Upload and process geospatial file",
    description="Accepts KML (.kml) or Shapefile ZIP (.zip) files, calculates metric feature measurements (area in m2, length in m), and stores results.",
    responses={
        400: {"model": ErrorResponse, "description": "Invalid file, unsupported type, or corrupted geospatial data."},
        422: {"model": ErrorResponse, "description": "Validation error."},
        500: {"model": ErrorResponse, "description": "Internal server error."}
    }
)
async def upload_file(
    file: UploadFile = File(...),
    service: FileService = Depends(get_file_service)
) -> FileUploadResponse:
    """Uploads and processes a geospatial file (.kml or .zip)."""
    return await service.process_file(file)


@router.get(
    "/{file_id}/",
    response_model=FileDetailResponse,
    status_code=status.HTTP_200_OK,
    summary="Get file processing metadata",
    description="Retrieves status, feature count, and source CRS metadata for an uploaded file by ID.",
    responses={
        404: {"model": ErrorResponse, "description": "File not found."},
        500: {"model": ErrorResponse, "description": "Internal server error."}
    }
)
async def get_file_info(
    file_id: str,
    service: FileService = Depends(get_file_service)
) -> FileDetailResponse:
    """Retrieves metadata for an uploaded file by ID."""
    return service.get_file_info(file_id)


@router.get(
    "/{file_id}/measurements/",
    response_model=FileMeasurementsResponse,
    status_code=status.HTTP_200_OK,
    summary="Get calculated feature measurements",
    description="Retrieves the list of feature measurements (area/length/none) for a processed file.",
    responses={
        404: {"model": ErrorResponse, "description": "File not found."},
        500: {"model": ErrorResponse, "description": "Internal server error."}
    }
)
async def get_file_measurements(
    file_id: str,
    service: FileService = Depends(get_file_service)
) -> FileMeasurementsResponse:
    """Retrieves feature measurement results for a file ID."""
    return service.get_file_measurements(file_id)
