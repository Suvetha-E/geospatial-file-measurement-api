# Geospatial File Measurement API

A modular backend service built with **FastAPI**, **GeoPandas**, **Shapely**, **PyProj**, **SQLite**, and **SQLAlchemy 2.x**. The API accepts geospatial dataset uploads (`.kml` and `.zip` Shapefiles), handles Coordinate Reference Systems (CRS) correctly through metric projected transformations, calculates spatial measurements (Polygon area in $\text{m}^2$, LineString length in $\text{m}$), stores metadata and results in SQLite, and exposes REST endpoints.

---

## Features

- **Format Support**: Upload and process `.kml` files and `.zip` Shapefiles containing required companion files (`.shp`, `.dbf`, `.shx`, `.prj`).
- **Feature Extraction**: Extracts feature ID/index, geometry type, raw geometry, CRS metadata, and attribute properties for every feature.
- **Accurate Metric Measurements**:
  - **Polygon / MultiPolygon**: Calculates area in square meters ($\text{m}^2$).
  - **LineString / MultiLineString**: Calculates length in meters ($\text{m}$).
  - **Point / MultiPoint**: Handled without error (`null` measurement values, status `SUCCESS`).
  - **Unsupported / Invalid Geometries**: Handled gracefully at the feature level (`SKIPPED` or `ERROR` status) without failing the entire file request.
- **Projected CRS Transformations**: Transforms geographic coordinates ($\text{EPSG:4326}$ degrees) into optimal Universal Transverse Mercator (UTM) metric projections before spatial measurement.
- **Strict 3-Tier Architecture**: Separation of concerns across Router, Service, and Repository layers.
- **Database Persistence**: SQLite database managed via SQLAlchemy 2.x ORM and Alembic migrations.
- **Centralized Error Handling**: Standardized JSON error contracts across domain exceptions and validation errors.

---

## Tech Stack

- **Framework**: Python 3.12+, FastAPI, Uvicorn
- **Geospatial Stack**: GeoPandas, Shapely 2.x, PyProj, Pyogrio, Pyshp
- **Database & Persistence**: SQLite, SQLAlchemy 2.x, Alembic
- **Validation & Settings**: Pydantic v2, Pydantic-Settings
- **Testing**: Pytest, Pytest-Asyncio, HTTPX / TestClient

---

## Architecture

The application enforces a strict three-tier architecture with dedicated geospatial processing services:

```text
               +-----------------------------+
               |     Router / API Layer      |
               | (app/api/routers/files.py)  |
               +--------------+--------------+
                              |
                              v
               +-----------------------------+
               |        Service Layer        |
               | (File, Geospatial, CRS,     |
               |     Measurement Services)   |
               +--------------+--------------+
                              |
                              v
               +-----------------------------+
               |      Repository Layer       |
               |(app/repositories/file_repo) |
               +--------------+--------------+
                              |
                              v
               +-----------------------------+
               |     SQLite Database         |
               |  (SQLAlchemy 2.x / Alembic) |
               +-----------------------------+
```

### Module Structure

```text
geospatial-file-measurement-api/
├── app/
│   ├── main.py
│   ├── core/
│   │   ├── config.py
│   │   ├── database.py
│   │   ├── logging.py
│   │   └── exceptions.py
│   ├── api/
│   │   ├── dependencies.py
│   │   └── routers/
│   │       └── files.py
│   ├── models/
│   │   └── file.py
│   ├── schemas/
│   │   ├── file.py
│   │   ├── measurement.py
│   │   └── error.py
│   ├── services/
│   │   ├── file_service.py
│   │   ├── geospatial_service.py
│   │   ├── measurement_service.py
│   │   └── crs_service.py
│   ├── repositories/
│   │   └── file_repository.py
│   ├── exceptions/
│   │   ├── base.py
│   │   ├── file_exceptions.py
│   │   ├── geospatial_exceptions.py
│   │   └── handlers.py
│   └── utils/
│       ├── file_utils.py
│       └── geometry_utils.py
├── tests/
│   ├── conftest.py
│   ├── unit/
│   ├── integration/
│   └── api/
├── alembic/
├── uploads/
├── .env.example
├── .gitignore
├── alembic.ini
├── requirements.txt
├── README.md
└── pyproject.toml
```

---

## File Processing Flow

```text
Upload File (POST /api/files/)
       ↓
Validate Extension & Size (file_utils)
       ↓
Stream Chunks & Save with UUID Filename
       ↓
Create DB Record (Status: UPLOADED)
       ↓
Extract ZIP if Shapefile (Status: PROCESSING)
       ↓
Read Features & Extract Source CRS (GeospatialService)
       ↓
Determine Local UTM Projected CRS (CRSService)
       ↓
Transform Coordinates (Source CRS → Projected CRS)
       ↓
Calculate Metric Area / Length (MeasurementService)
       ↓
Persist Measurements & Update DB Record (Status: COMPLETED)
       ↓
Clean Up Temp Directory & Return Response Schema
```

---

## CRS Handling

### Geographic Coordinate Transformation
Geographic Coordinate Reference Systems (such as **WGS84 / EPSG:4326**) express spatial locations in **angular degrees** ($\text{longitude}, \text{latitude}$). Because degrees do not represent uniform linear distances across latitudes, calculating metric area or length directly on $\text{EPSG:4326}$ coordinates produces mathematically invalid results.

### Projected CRS Selection Strategy
1. **KML Semantics**: KML files standardize on WGS84 ($\text{EPSG:4326}$) per OpenGIS specifications.
2. **Shapefile Metadata Strictness**: Shapefiles are inspected for `.prj` spatial reference metadata. If a `.prj` file is missing or unparseable, the system **rejects the upload** with a `MISSING_CRS` error (status `400 Bad Request`) and sets the database status to `FAILED`. The system does **not** silently assume $\text{EPSG:4326}$ for CRS-less Shapefiles.
3. **Centroid-Based UTM Selection**: For geographic coordinates, `CRSService` calculates the centroid $(\text{longitude}, \text{latitude})$ of the feature and determines the optimal Universal Transverse Mercator (UTM) zone:
   $$\text{Zone} = \lfloor \frac{\text{Longitude} + 180}{6} \rfloor + 1$$
   - Northern Hemisphere ($\text{Latitude} \ge 0$): `EPSG:32600 + Zone`
   - Southern Hemisphere ($\text{Latitude} < 0$): `EPSG:32700 + Zone`
4. **Reprojection**: Geometries are reprojected into the target metric CRS via `pyproj.Transformer` before spatial calculations are performed.

---

## Measurements

- **Polygon / MultiPolygon**: Area in square meters ($\text{m}^2$), rounded to 2 decimal places (`measurement_type = "area"`, `measurement_unit = "m2"`).
- **LineString / MultiLineString**: Length in meters ($\text{m}$), rounded to 2 decimal places (`measurement_type = "length"`, `measurement_unit = "m"`).
- **Point / MultiPoint**: No measurement required (`measurement_type = null`, `measurement_value = null`, status `SUCCESS`).
- **Unsupported Geometries**: Returned with status `SKIPPED` and an explanatory error message without crashing the overall request.

---

## API Documentation

FastAPI automatically generates interactive documentation at:
- **Swagger UI**: `http://localhost:8000/docs`
- **ReDoc UI**: `http://localhost:8000/redoc`

### Endpoints

#### Upload File
- **Method**: `POST`
- **URL**: `/api/files/`
- **Payload**: `multipart/form-data` with `file` (`.kml` or `.zip` Shapefile).
- **Response** (`201 Created`):
```json
{
  "id": "c9b13998-ef78-43d9-95e2-45e0fef3d902",
  "filename": "c9b13998-ef78-43d9-95e2-45e0fef3d902.kml",
  "feature_count": 3,
  "crs": "EPSG:4326",
  "status": "COMPLETED"
}
```

#### Get File Information
- **Method**: `GET`
- **URL**: `/api/files/{file_id}/`
- **Response** (`200 OK`):
```json
{
  "id": "c9b13998-ef78-43d9-95e2-45e0fef3d902",
  "filename": "c9b13998-ef78-43d9-95e2-45e0fef3d902.kml",
  "original_filename": "london_survey.kml",
  "feature_count": 3,
  "crs": "EPSG:4326",
  "status": "COMPLETED",
  "created_at": "2026-10-07T20:55:00Z",
  "updated_at": "2026-10-07T20:55:01Z"
}
```

#### Get Measurements
- **Method**: `GET`
- **URL**: `/api/files/{file_id}/measurements/`
- **Response** (`200 OK`):
```json
{
  "file_id": "c9b13998-ef78-43d9-95e2-45e0fef3d902",
  "measurements": [
    {
      "feature_id": 0,
      "geometry_type": "Polygon",
      "measurement_type": "area",
      "measurement_value": 770142.85,
      "measurement_unit": "m2",
      "processing_status": "SUCCESS",
      "error_message": null,
      "properties": {
        "name": "Zone Alpha Polygon"
      }
    },
    {
      "feature_id": 1,
      "geometry_type": "LineString",
      "measurement_type": "length",
      "measurement_value": 1802.43,
      "measurement_unit": "m",
      "processing_status": "SUCCESS",
      "error_message": null,
      "properties": {
        "name": "Transect Line"
      }
    },
    {
      "feature_id": 2,
      "geometry_type": "Point",
      "measurement_type": null,
      "measurement_value": null,
      "measurement_unit": null,
      "processing_status": "SUCCESS",
      "error_message": null,
      "properties": {
        "name": "Monitoring Point"
      }
    }
  ]
}
```

#### Health Check
- **Method**: `GET`
- **URL**: `/health`
- **Response** (`200 OK`):
```json
{
  "status": "healthy",
  "project": "Geospatial File Measurement API",
  "version": "1.0.0"
}
```

---

## Error Handling

The application centralizes exception handling to convert domain exceptions into uniform JSON contracts:

```json
{
  "error": {
    "code": "MISSING_CRS",
    "message": "Shapefile is missing a .prj file or spatial reference metadata (CRS)."
  }
}
```

### Common Error Codes
- `UNSUPPORTED_FILE_TYPE` (HTTP 400): Extension is not `.kml` or `.zip`.
- `INVALID_FILE` (HTTP 400): Empty upload, size limit exceeded, or corrupted format.
- `INVALID_ZIP` (HTTP 400): Unreadable ZIP archive or unsafe ZIP entry path.
- `SHAPEFILE_NOT_FOUND` (HTTP 400): ZIP archive lacks a `.shp` file.
- `MISSING_CRS` (HTTP 400): Shapefile lacks required `.prj` spatial metadata.
- `RESOURCE_NOT_FOUND` (HTTP 404): Requested file ID does not exist.
- `VALIDATION_ERROR` (HTTP 422): Invalid request parameters.

---

## Security & File Handling

- **Chunked Upload Streaming**: Uploads stream in 1 MB chunks while accumulating file size on disk, enforcing `MAX_UPLOAD_SIZE` without loading entire files into RAM.
- **ZIP Path Traversal Protection**: Inspects all ZIP archive member paths (`target_dir_resolved` check) to prevent directory traversal attacks (e.g. `../evil.txt`).
- **Filename Sanitization**: Uploaded files are stored on disk using generated `UUID` filenames.
- **Temporary Cleanup**: Temporary extraction directories and partial upload files are unlinked in `finally` blocks upon completion or failure.
- **No Execution**: Uploaded files are parsed purely as data; no uploaded file content is executed.

---

## Configuration

Environment variables are loaded via Pydantic Settings (`.env`):

| Variable | Default Value | Description |
| :--- | :--- | :--- |
| `PROJECT_NAME` | `Geospatial File Measurement API` | Application title |
| `VERSION` | `1.0.0` | API version |
| `ENVIRONMENT` | `development` | Runtime environment |
| `LOG_LEVEL` | `INFO` | Standard logging verbosity |
| `DATABASE_URL` | `sqlite:///./geospatial.db` | SQLAlchemy database URL |
| `UPLOAD_DIRECTORY` | `./uploads` | Storage path for uploaded files |
| `TEMP_DIRECTORY` | `./temp` | Temporary extraction directory |
| `MAX_UPLOAD_SIZE` | `52428800` | Maximum upload size in bytes (50 MB) |

---

## Setup and Running

### 1. Prerequisites
- Python 3.12 or newer.

### 2. Virtual Environment Setup
```bash
python -m venv .venv
# Windows PowerShell:
.venv\Scripts\Activate.ps1
# Linux/macOS:
source .venv/bin/activate
```

### 3. Install Dependencies
```bash
pip install -r requirements.txt
```

### 4. Database Setup & Migrations
```bash
alembic upgrade head
```

### 5. Run the Application
```bash
uvicorn app.main:app --reload --port 8000
```
The server will start at `http://localhost:8000`.

---

## Testing

The project includes unit, integration, and end-to-end API tests built with Pytest:

```bash
# Run all tests
pytest -v
```

### Tested Scenarios
- Valid KML upload, feature parsing, metric area/length calculation, and point handling.
- Valid Shapefile ZIP upload with full `.shp`, `.shx`, `.dbf`, `.prj` components.
- CRS-less Shapefile rejection (`MISSING_CRS` error and `FAILED` processing status).
- ZIP path traversal attack rejection.
- Upload size limit enforcement via chunked streaming.
- Empty file, corrupted KML, and invalid archive rejection.
- SQLite repository CRUD operations and database connection handling.
- PyProj UTM CRS determination and coordinate reprojecting math.

---

## Design Decisions

- **FastAPI**: Provides asynchronous endpoint support, automatic OpenAPI/Swagger documentation, and native Pydantic validation.
- **Three-Tier Architecture**: Decouples HTTP request routing from domain services and database persistence, enabling independent testing of business logic.
- **SQLAlchemy 2.x & Alembic**: Provides type-safe database queries and migration management.
- **Dynamic UTM Reprojection**: Calculates accurate metric area ($\text{m}^2$) and length ($\text{m}$) without relying on imprecise geographic degree calculations.
- **Strict CRS Policy**: Rejects Shapefiles missing `.prj` metadata to prevent incorrect coordinate assumptions.
- **ElementTree KML Parser**: Parses KML placemarks natively using XML element trees, avoiding external OS system driver dependencies.

---

## Learning

- **Spatial Reference Mathematics**: Mastered the distinction between geographic and projected coordinate reference systems and UTM zone selection algorithms.
- **PyProj & Shapely Integration**: Applied coordinate transformations across Shapely geometry objects using PyProj transformers.
- **Secure File Handling**: Implemented chunked upload streaming and path-traversal validation for compressed archives.
- **Clean Architecture**: Built a modular, testable backend application following separation of concerns.

---

## Future Scope

- **PostgreSQL / PostGIS**: Transition from SQLite to PostGIS for native spatial indexing and server-side spatial queries.
- **Asynchronous Task Queue**: Integrate Celery or Redis background workers to process massive multi-gigabyte geospatial datasets asynchronously.
- **Object Storage Integration**: Store uploaded datasets in Amazon S3 or Google Cloud Storage.
- **GeoJSON Output**: Expose endpoints returning feature geometries as standardized GeoJSON FeatureCollections.
