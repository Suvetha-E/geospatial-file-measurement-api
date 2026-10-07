from typing import Optional, Tuple
from shapely.geometry import base, shape
from shapely.validation import make_valid


def is_geometry_valid(geom: Optional[base.BaseGeometry]) -> bool:
    """Checks if a Shapely geometry is non-null, non-empty, and valid."""
    if geom is None or geom.is_empty:
        return False
    return geom.is_valid


def ensure_valid_geometry(geom: Optional[base.BaseGeometry]) -> Optional[base.BaseGeometry]:
    """Attempts to fix invalid geometry using shapely.validation.make_valid."""
    if geom is None or geom.is_empty:
        return None
    if not geom.is_valid:
        try:
            geom = make_valid(geom)
        except Exception:
            return None
    return geom


def get_geometry_centroid_coords(geom: base.BaseGeometry) -> Tuple[float, float]:
    """Returns (longitude, latitude) or (x, y) centroid coordinates of geometry."""
    centroid = geom.centroid
    return centroid.x, centroid.y
