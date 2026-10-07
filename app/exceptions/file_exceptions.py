from typing import Optional, Dict, Any
from app.exceptions.base import AppException


class FileProcessingException(AppException):
    """Base exception for file processing issues."""
    def __init__(
        self,
        message: str,
        code: str = "FILE_PROCESSING_ERROR",
        status_code: int = 400,
        details: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(message=message, code=code, status_code=status_code, details=details)


class UnsupportedFileTypeException(FileProcessingException):
    def __init__(self, message: str = "Only KML files and ZIP files containing Shapefiles are supported."):
        super().__init__(
            message=message,
            code="UNSUPPORTED_FILE_TYPE",
            status_code=400
        )


class InvalidFileException(FileProcessingException):
    def __init__(self, message: str = "The uploaded file is invalid or corrupted."):
        super().__init__(
            message=message,
            code="INVALID_FILE",
            status_code=400
        )


class InvalidZipException(FileProcessingException):
    def __init__(self, message: str = "The uploaded ZIP file is invalid or unreadable."):
        super().__init__(
            message=message,
            code="INVALID_ZIP",
            status_code=400
        )


class ShapefileNotFoundException(FileProcessingException):
    def __init__(self, message: str = "No valid .shp file found inside the ZIP archive."):
        super().__init__(
            message=message,
            code="SHAPEFILE_NOT_FOUND",
            status_code=400
        )


class ResourceNotFoundException(AppException):
    def __init__(self, message: str = "Requested resource not found."):
        super().__init__(
            message=message,
            code="RESOURCE_NOT_FOUND",
            status_code=404
        )
