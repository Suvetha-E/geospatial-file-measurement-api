import re
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import List, Dict, Any, Tuple, Optional
import geopandas as gpd
from pyproj import CRS
from shapely.geometry import (
    Point, LineString, Polygon, MultiPolygon, MultiLineString, MultiPoint, GeometryCollection, shape
)
import shapefile

from app.core.logging import logger
from app.exceptions.geospatial_exceptions import (
    InvalidGeometryException,
    MissingCRSException,
    GeospatialException
)
from app.exceptions.file_exceptions import InvalidFileException


class GeospatialService:
    """Service for extracting geometries, properties, and CRS from geospatial data files."""

    def read_file_features(self, file_path: Path, ext: str) -> Tuple[List[Dict[str, Any]], str]:
        """
        Reads geospatial file (.kml or .shp) and returns a list of feature dictionaries
        along with the detected source CRS string.
        """
        ext = ext.lower()
        if ext == ".kml":
            return self._read_kml(file_path)
        elif ext == ".shp" or ext == ".zip":
            return self._read_shapefile(file_path)
        else:
            raise InvalidFileException(f"Unsupported geospatial format: {ext}")

    def _read_shapefile(self, shp_path: Path) -> Tuple[List[Dict[str, Any]], str]:
        """Reads shapefile using GeoPandas / Pyogrio / Pyshp."""
        # Require .prj file to exist and be non-empty
        prj_path = shp_path.with_suffix(".prj")
        if not prj_path.exists() or not prj_path.read_text(encoding="utf-8", errors="ignore").strip():
            raise MissingCRSException("Shapefile is missing a .prj file or spatial reference metadata (CRS).")

        try:
            gdf = gpd.read_file(shp_path)
            source_crs_str = None
            if gdf.crs is not None:
                try:
                    source_crs_str = gdf.crs.to_string()
                except Exception:
                    source_crs_str = str(gdf.crs)

            if not source_crs_str:
                wkt = prj_path.read_text(encoding="utf-8", errors="ignore").strip()
                try:
                    c = CRS.from_user_input(wkt)
                    source_crs_str = c.to_string()
                except Exception as ex:
                    raise MissingCRSException(f"Shapefile contains an invalid or unparseable .prj CRS: {str(ex)}")

            features = []
            for idx, row in gdf.iterrows():
                geom = row.geometry
                geom_type = geom.geom_type if geom is not None else "Unknown"

                # Extract properties without geometry column
                props = {}
                for col in gdf.columns:
                    if col != gdf.geometry.name:
                        val = row[col]
                        # Convert non-serializable objects to string
                        if isinstance(val, (int, float, str, type(None), bool)):
                            props[col] = val
                        else:
                            props[col] = str(val)

                features.append({
                    "feature_id": int(idx),
                    "geometry_type": geom_type,
                    "geometry": geom,
                    "properties": props
                })

            return features, source_crs_str

        except GeospatialException:
            raise
        except Exception as e:
            logger.warning(f"GeoPandas shapefile read failed: {e}. Attempting fallback with pyshp...")
            return self._read_shapefile_pyshp(shp_path)

    def _read_shapefile_pyshp(self, shp_path: Path) -> Tuple[List[Dict[str, Any]], str]:
        """Fallback Shapefile reader using pure-python pyshp."""
        prj_path = shp_path.with_suffix(".prj")
        if not prj_path.exists():
            raise MissingCRSException("Shapefile is missing a .prj file (CRS metadata).")
        
        wkt = prj_path.read_text(encoding="utf-8", errors="ignore").strip()
        if not wkt:
            raise MissingCRSException("Shapefile .prj file is empty.")

        try:
            c = CRS.from_user_input(wkt)
            source_crs_str = c.to_string()
        except Exception as ex:
            raise MissingCRSException(f"Could not parse Shapefile .prj file: {str(ex)}")

        try:
            sf = shapefile.Reader(str(shp_path))
            features = []
            fields = [f[0] for f in sf.fields[1:]]

            for idx, shape_record in enumerate(sf.shapeRecords()):
                sh = shape_record.shape
                record = shape_record.record
                
                # Convert shape to Shapely
                geom = shape(sh.__geo_interface__)
                geom_type = geom.geom_type if geom else "Unknown"

                props = {fields[i]: record[i] for i in range(len(fields))}

                features.append({
                    "feature_id": idx,
                    "geometry_type": geom_type,
                    "geometry": geom,
                    "properties": props
                })

            return features, source_crs_str

        except GeospatialException:
            raise
        except Exception as e:
            logger.error(f"Failed to parse shapefile with pyshp: {e}")
            raise InvalidFileException(f"Could not read shapefile: {str(e)}")

    def _read_kml(self, kml_path: Path) -> Tuple[List[Dict[str, Any]], str]:
        """Parses KML file into features and returns default EPSG:4326 CRS."""
        try:
            tree = ET.parse(kml_path)
            root = tree.getroot()
        except Exception as e:
            logger.error(f"Failed to parse KML XML structure: {e}")
            raise InvalidFileException(f"Invalid or corrupted KML file: {str(e)}")

        # Strip namespace if present
        namespace = ""
        m = re.match(r"\{(.*)\}", root.tag)
        if m:
            namespace = m.group(1)

        ns = {"kml": namespace} if namespace else {}

        placemarks = root.findall(".//kml:Placemark", ns) if namespace else root.findall(".//Placemark")
        features = []

        for idx, pm in enumerate(placemarks):
            name_el = pm.find("kml:name", ns) if namespace else pm.find("name")
            desc_el = pm.find("kml:description", ns) if namespace else pm.find("description")

            props = {}
            if name_el is not None and name_el.text:
                props["name"] = name_el.text.strip()
            if desc_el is not None and desc_el.text:
                props["description"] = desc_el.text.strip()

            # Parse ExtendedData
            ext_data = pm.find("kml:ExtendedData", ns) if namespace else pm.find("ExtendedData")
            if ext_data is not None:
                data_elements = ext_data.findall("kml:Data", ns) if namespace else ext_data.findall("Data")
                for d in data_elements:
                    d_name = d.attrib.get("name")
                    val_el = d.find("kml:value", ns) if namespace else d.find("value")
                    if d_name and val_el is not None and val_el.text:
                        props[d_name] = val_el.text.strip()

            geom = self._parse_kml_geometry(pm, ns, namespace)
            geom_type = geom.geom_type if geom is not None else "Unknown"

            features.append({
                "feature_id": idx,
                "geometry_type": geom_type,
                "geometry": geom,
                "properties": props
            })

        return features, "EPSG:4326"

    def _parse_kml_geometry(self, element: ET.Element, ns: dict, namespace: str) -> Optional[Any]:
        """Extracts Shapely geometry from a KML element."""
        # Check Polygon
        poly_el = element.find(".//kml:Polygon", ns) if namespace else element.find(".//Polygon")
        if poly_el is not None:
            return self._parse_kml_polygon(poly_el, ns, namespace)

        # Check LineString
        line_el = element.find(".//kml:LineString", ns) if namespace else element.find(".//LineString")
        if line_el is not None:
            return self._parse_kml_linestring(line_el, ns, namespace)

        # Check Point
        pt_el = element.find(".//kml:Point", ns) if namespace else element.find(".//Point")
        if pt_el is not None:
            return self._parse_kml_point(pt_el, ns, namespace)

        return None

    def _parse_kml_coords(self, coords_text: str) -> List[Tuple[float, float]]:
        """Parses KML coordinate text into list of (longitude, latitude) tuples."""
        coords = []
        for token in coords_text.strip().split():
            parts = token.split(",")
            if len(parts) >= 2:
                try:
                    lon = float(parts[0])
                    lat = float(parts[1])
                    coords.append((lon, lat))
                except ValueError:
                    continue
        return coords

    def _parse_kml_point(self, pt_el: ET.Element, ns: dict, namespace: str) -> Optional[Point]:
        coords_el = pt_el.find("kml:coordinates", ns) if namespace else pt_el.find("coordinates")
        if coords_el is not None and coords_el.text:
            coords = self._parse_kml_coords(coords_el.text)
            if coords:
                return Point(coords[0])
        return None

    def _parse_kml_linestring(self, line_el: ET.Element, ns: dict, namespace: str) -> Optional[LineString]:
        coords_el = line_el.find("kml:coordinates", ns) if namespace else line_el.find("coordinates")
        if coords_el is not None and coords_el.text:
            coords = self._parse_kml_coords(coords_el.text)
            if len(coords) >= 2:
                return LineString(coords)
        return None

    def _parse_kml_polygon(self, poly_el: ET.Element, ns: dict, namespace: str) -> Optional[Polygon]:
        outer_el = poly_el.find(".//kml:outerBoundaryIs//kml:coordinates", ns) if namespace else poly_el.find(".//outerBoundaryIs//coordinates")
        if outer_el is None or not outer_el.text:
            return None

        outer_coords = self._parse_kml_coords(outer_el.text)
        if len(outer_coords) < 3:
            return None

        inner_coords_list = []
        inner_els = poly_el.findall(".//kml:innerBoundaryIs//kml:coordinates", ns) if namespace else poly_el.findall(".//innerBoundaryIs//coordinates")
        for in_el in inner_els:
            if in_el.text:
                ic = self._parse_kml_coords(in_el.text)
                if len(ic) >= 3:
                    inner_coords_list.append(ic)

        return Polygon(shell=outer_coords, holes=inner_coords_list)
