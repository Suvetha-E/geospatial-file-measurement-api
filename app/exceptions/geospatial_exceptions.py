from typing import Optional, Dict, Any
from app.exceptions.base import AppException


class GeospatialException(AppException):
    """Base exception for geospatial processing errors."""
    def __init__(
        self,
        message: str,
        code: str = "GEOSPATIAL_ERROR",
        status_code: int = 400,
        details: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(message=message, code=code, status_code=status_code, details=details)


class InvalidGeometryException(GeospatialException):
    def __init__(self, message: str = "The feature geometry is invalid or unparseable."):
        super().__init__(
            message=message,
            code="INVALID_GEOMETRY",
            status_code=400
        )


class MissingCRSException(GeospatialException):
    def __init__(self, message: str = "The spatial reference / CRS is missing or unidentifiable."):
        super().__init__(
            message=message,
            code="MISSING_CRS",
            status_code=400
        )


class UnsupportedGeometryException(GeospatialException):
    def __init__(self, message: str = "The geometry type is not supported for metric measurement."):
        super().__init__(
            message=message,
            code="UNSUPPORTED_GEOMETRY",
            status_code=400
        )
