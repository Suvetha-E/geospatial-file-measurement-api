import io
import os
import zipfile
import pytest
from pathlib import Path
from typing import Generator
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import StaticPool
from fastapi.testclient import TestClient
from shapely.geometry import Polygon, LineString, Point
import shapefile

from app.main import app
from app.core.database import Base, get_db
from app.core.config import settings


# In-memory SQLite for testing using StaticPool to preserve tables across connections
TEST_DATABASE_URL = "sqlite:///:memory:"

engine = create_engine(
    TEST_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
    future=True
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


@pytest.fixture(scope="function")
def db_session() -> Generator[Session, None, None]:
    """Creates a fresh in-memory database session for a test."""
    Base.metadata.create_all(bind=engine)
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(bind=engine)


@pytest.fixture(scope="function")
def client(db_session: Session) -> Generator[TestClient, None, None]:
    """FastAPI TestClient with overridden DB dependency."""
    def override_get_db():
        try:
            yield db_session
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


@pytest.fixture
def sample_polygon() -> Polygon:
    """Returns a simple WGS84 polygon around London (lon, lat)."""
    return Polygon([
        (-0.12, 51.50),
        (-0.12, 51.51),
        (-0.11, 51.51),
        (-0.11, 51.50),
        (-0.12, 51.50)
    ])


@pytest.fixture
def sample_linestring() -> LineString:
    """Returns a simple WGS84 LineString."""
    return LineString([
        (-0.12, 51.50),
        (-0.12, 51.51),
        (-0.11, 51.51)
    ])


@pytest.fixture
def sample_point() -> Point:
    """Returns a simple WGS84 Point."""
    return Point(-0.12, 51.50)


@pytest.fixture
def sample_kml_bytes() -> bytes:
    """Returns valid KML file content as bytes."""
    kml_content = """<?xml version="1.0" encoding="UTF-8"?>
<kml xmlns="http://www.opengis.net/kml/2.2">
  <Document>
    <name>Test Survey Document</name>
    <Placemark>
      <name>Zone Alpha Polygon</name>
      <description>Survey field polygon</description>
      <Polygon>
        <outerBoundaryIs>
          <LinearRing>
            <coordinates>
              -0.12,51.50,0
              -0.12,51.51,0
              -0.11,51.51,0
              -0.11,51.50,0
              -0.12,51.50,0
            </coordinates>
          </LinearRing>
        </outerBoundaryIs>
      </Polygon>
    </Placemark>
    <Placemark>
      <name>Transect Line</name>
      <LineString>
        <coordinates>
          -0.12,51.50,0
          -0.12,51.51,0
          -0.11,51.51,0
        </coordinates>
      </LineString>
    </Placemark>
    <Placemark>
      <name>Monitoring Point</name>
      <Point>
        <coordinates>-0.12,51.50,0</coordinates>
      </Point>
    </Placemark>
  </Document>
</kml>
"""
    return kml_content.encode("utf-8")


@pytest.fixture
def sample_shapefile_zip_bytes() -> bytes:
    """Creates a valid Shapefile (.shp, .shx, .dbf, .prj) in memory and returns a ZIP archive as bytes."""
    zip_buffer = io.BytesIO()
    shp_buffer = io.BytesIO()
    shx_buffer = io.BytesIO()
    dbf_buffer = io.BytesIO()

    w = shapefile.Writer(shp=shp_buffer, shx=shx_buffer, dbf=dbf_buffer, shapeType=shapefile.POLYGON)
    w.field('name', 'C', '40')
    w.field('category', 'C', '20')

    # Add a polygon feature
    w.poly([[
        [-0.12, 51.50],
        [-0.12, 51.51],
        [-0.11, 51.51],
        [-0.11, 51.50],
        [-0.12, 51.50]
    ]])
    w.record('Parcel A', 'Agriculture')

    # Add a second polygon feature
    w.poly([[
        [-0.10, 51.52],
        [-0.10, 51.53],
        [-0.09, 51.53],
        [-0.09, 51.52],
        [-0.10, 51.52]
    ]])
    w.record('Parcel B', 'Residential')

    w.close()

    # WGS84 PRJ text
    prj_wkt = 'GEOGCS["GCS_WGS_1984",DATUM["D_WGS_1984",SPHEROID["WGS_1984",6378137.0,298.257223563]],PRIMEM["Greenwich",0.0],UNIT["Degree",0.0174532925199433]]'

    with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zf:
        zf.writestr('survey_parcels.shp', shp_buffer.getvalue())
        zf.writestr('survey_parcels.shx', shx_buffer.getvalue())
        zf.writestr('survey_parcels.dbf', dbf_buffer.getvalue())
        zf.writestr('survey_parcels.prj', prj_wkt)

    return zip_buffer.getvalue()


@pytest.fixture
def corrupted_kml_bytes() -> bytes:
    """Returns invalid/corrupted XML content."""
    return b"<?xml version='1.0'?><kml><Document><Placemark><Polygon>Unclosed tags..."


@pytest.fixture
def invalid_zip_bytes() -> bytes:
    """Returns random bytes that are not a ZIP archive."""
    return b"This is not a zip file content at all!"


@pytest.fixture
def zip_without_shp_bytes() -> bytes:
    """Returns a valid ZIP archive missing a .shp file."""
    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, 'w') as zf:
        zf.writestr('readme.txt', 'This archive contains no shapefile.')
    return zip_buffer.getvalue()


@pytest.fixture
def shapefile_zip_without_prj_bytes() -> bytes:
    """Creates a valid Shapefile ZIP archive missing the required .prj file."""
    zip_buffer = io.BytesIO()
    shp_buffer = io.BytesIO()
    shx_buffer = io.BytesIO()
    dbf_buffer = io.BytesIO()

    w = shapefile.Writer(shp=shp_buffer, shx=shx_buffer, dbf=dbf_buffer, shapeType=shapefile.POLYGON)
    w.field('name', 'C', '40')
    w.poly([[[-0.12, 51.50], [-0.12, 51.51], [-0.11, 51.51], [-0.11, 51.50], [-0.12, 51.50]]])
    w.record('Parcel A')
    w.close()

    with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zf:
        zf.writestr('survey_no_prj.shp', shp_buffer.getvalue())
        zf.writestr('survey_no_prj.shx', shx_buffer.getvalue())
        zf.writestr('survey_no_prj.dbf', dbf_buffer.getvalue())
        # Intentionally omit .prj file

    return zip_buffer.getvalue()


@pytest.fixture
def path_traversal_zip_bytes() -> bytes:
    """Creates a ZIP archive containing a path traversal member name."""
    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, 'w') as zf:
        zf.writestr('../evil_script.sh', 'echo Hacked!')
        zf.writestr('survey.shp', b'dummy shp content')
    return zip_buffer.getvalue()

