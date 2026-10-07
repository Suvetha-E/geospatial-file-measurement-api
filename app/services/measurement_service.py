from typing import Dict, Any, Optional, Tuple
from shapely.geometry import base, Polygon, MultiPolygon, LineString, MultiLineString, Point, MultiPoint
from app.utils.geometry_utils import ensure_valid_geometry
from app.core.logging import logger


class MeasurementService:
    """Service for calculating metric spatial measurements (area, length)."""

    def calculate_measurement(
        self,
        geometry: Optional[base.BaseGeometry],
        geometry_type: str
    ) -> Tuple[Optional[str], Optional[float], Optional[str], str, Optional[str]]:
        """
        Calculates measurement for a given geometry in projected coordinates.

        Returns tuple of:
        (measurement_type, measurement_value, measurement_unit, processing_status, error_message)
        """
        if geometry is None or geometry.is_empty:
            return None, None, None, "ERROR", "Empty or missing geometry"

        valid_geom = ensure_valid_geometry(geometry)
        if valid_geom is None:
            return None, None, None, "ERROR", "Invalid geometry that could not be repaired"

        g_type = valid_geom.geom_type

        # Polygon / MultiPolygon -> Area in m2
        if g_type in ("Polygon", "MultiPolygon"):
            try:
                area_m2 = round(float(valid_geom.area), 2)
                return "area", area_m2, "m2", "SUCCESS", None
            except Exception as e:
                logger.error(f"Error calculating polygon area: {e}")
                return None, None, None, "ERROR", f"Area calculation failed: {str(e)}"

        # LineString / MultiLineString -> Length in m
        elif g_type in ("LineString", "MultiLineString"):
            try:
                length_m = round(float(valid_geom.length), 2)
                return "length", length_m, "m", "SUCCESS", None
            except Exception as e:
                logger.error(f"Error calculating line length: {e}")
                return None, None, None, "ERROR", f"Length calculation failed: {str(e)}"

        # Point / MultiPoint -> No measurement
        elif g_type in ("Point", "MultiPoint"):
            return None, None, None, "SUCCESS", None

        # Unsupported geometry type
        else:
            logger.info(f"Measurement not supported for geometry type: {g_type}")
            return None, None, None, "SKIPPED", f"Measurement not supported for geometry type: {g_type}"
