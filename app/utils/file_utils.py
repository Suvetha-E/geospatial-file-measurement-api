import os
import shutil
import uuid
import zipfile
from pathlib import Path
from typing import List, Tuple, Optional
from fastapi import UploadFile

from app.core.config import settings
from app.exceptions.file_exceptions import (
    UnsupportedFileTypeException,
    InvalidFileException,
    InvalidZipException,
    ShapefileNotFoundException
)


ALLOWED_EXTENSIONS = {".kml", ".zip"}


def generate_unique_filename(original_filename: str) -> str:
    """Generates a safe, unique filename using UUID while preserving extension."""
    ext = Path(original_filename).suffix.lower()
    return f"{uuid.uuid4().hex}{ext}"


def validate_upload_file(file: UploadFile) -> None:
    """Validates file extension and basic presence."""
    if not file.filename:
        raise InvalidFileException("Filename is missing.")

    ext = Path(file.filename).suffix.lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise UnsupportedFileTypeException(
            f"Unsupported file extension '{ext}'. Only KML files and ZIP files containing Shapefiles are supported."
        )


def extract_zip_safely(zip_path: Path, target_dir: Path) -> Path:
    """
    Safely extracts a ZIP file into target_dir preventing path traversal.
    Returns the path to the main .shp file.
    """
    if not zipfile.is_zipfile(zip_path):
        raise InvalidZipException("The uploaded file is not a valid ZIP archive.")

    with zipfile.ZipFile(zip_path, 'r') as zf:
        # Check members for path traversal vulnerabilities
        target_dir_resolved = target_dir.resolve()
        shp_members: List[zipfile.ZipInfo] = []

        for member in zf.infolist():
            member_path = (target_dir / member.filename).resolve()
            if not str(member_path).startswith(str(target_dir_resolved)):
                raise InvalidZipException(f"Unsafe ZIP member path detected: {member.filename}")

            if member.filename.lower().endswith(".shp") and not member.filename.startswith("__MACOSX"):
                shp_members.append(member)

        if not shp_members:
            raise ShapefileNotFoundException("No valid .shp file found inside the ZIP archive.")

        # Extract all files safely
        zf.extractall(target_dir)

        # Main shapefile path
        main_shp = target_dir / shp_members[0].filename
        return main_shp


def cleanup_directory(directory_path: Path) -> None:
    """Safely removes a temporary directory and its contents."""
    if directory_path and directory_path.exists():
        try:
            shutil.rmtree(directory_path, ignore_errors=True)
        except Exception:
            pass
