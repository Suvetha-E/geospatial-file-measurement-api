import math
from typing import Optional, Tuple, Any
from pyproj import CRS, Transformer
from shapely.geometry import base
from shapely.ops import transform
from app.core.logging import logger


class CRSService:
    """Service for handling Coordinate Reference Systems and spatial transformations."""

    DEFAULT_GEOGRAPHIC_CRS = "EPSG:4326"

    @staticmethod
    def parse_crs(crs_input: Optional[Any]) -> CRS:
        """Parses a CRS input (EPSG code, WKT, string) into a pyproj.CRS object."""
        if not crs_input:
            logger.info(f"No CRS provided. Falling back to default geographic CRS: {CRSService.DEFAULT_GEOGRAPHIC_CRS}")
            return CRS.from_user_input(CRSService.DEFAULT_GEOGRAPHIC_CRS)
        try:
            return CRS.from_user_input(crs_input)
        except Exception as e:
            logger.warning(f"Could not parse CRS '{crs_input}': {e}. Falling back to default {CRSService.DEFAULT_GEOGRAPHIC_CRS}")
            return CRS.from_user_input(CRSService.DEFAULT_GEOGRAPHIC_CRS)

    @staticmethod
    def determine_utm_crs(lon: float, lat: float) -> CRS:
        """Determines the appropriate projected UTM CRS for a given longitude and latitude."""
        # Clamp latitude to valid WGS84 bounds
        lat = max(-80.0, min(84.0, lat))
        
        # Calculate UTM zone
        zone = int(math.floor((lon + 180) / 6)) + 1
        zone = max(1, min(60, zone))

        if lat >= 0:
            epsg_code = 32600 + zone  # WGS 84 / UTM zone N
        else:
            epsg_code = 32700 + zone  # WGS 84 / UTM zone S

        return CRS.from_epsg(epsg_code)

    def get_projected_crs(self, source_crs: CRS, centroid_lon: float, centroid_lat: float) -> CRS:
        """
        Determines a suitable projected CRS (in meters) for metric measurements.
        If the source CRS is already projected, returns source_crs.
        If geographic, determines UTM zone based on centroid location.
        """
        if source_crs.is_projected:
            return source_crs
        
        return self.determine_utm_crs(centroid_lon, centroid_lat)

    def transform_geometry(
        self,
        geometry: base.BaseGeometry,
        source_crs: CRS,
        target_crs: CRS
    ) -> base.BaseGeometry:
        """
        Transforms a Shapely geometry from source CRS to target CRS.
        """
        if source_crs == target_crs or source_crs.equals(target_crs):
            return geometry

        transformer = Transformer.from_crs(source_crs, target_crs, always_xy=True)
        return transform(transformer.transform, geometry)
