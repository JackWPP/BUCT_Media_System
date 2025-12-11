"""
File storage service for handling photo uploads
"""
import os
import shutil
import uuid
from pathlib import Path
from typing import Optional
from fastapi import UploadFile
from app.core.config import get_settings

settings = get_settings()


def ensure_upload_dirs():
    """
    Ensure upload directories exist
    """
    upload_dir = Path(settings.UPLOAD_DIR)
    originals_dir = upload_dir / "originals"
    thumbnails_dir = upload_dir / "thumbnails"
    
    originals_dir.mkdir(parents=True, exist_ok=True)
    thumbnails_dir.mkdir(parents=True, exist_ok=True)
    
    return str(originals_dir), str(thumbnails_dir)


def generate_unique_filename(original_filename: str) -> tuple[str, str]:
    """
    Generate unique filename using UUID
    
    Returns:
        tuple: (uuid_str, file_extension)
    """
    file_extension = Path(original_filename).suffix.lower()
    uuid_str = str(uuid.uuid4())
    return uuid_str, file_extension


async def save_upload_file(
    upload_file: UploadFile,
    destination: str
) -> str:
    """
    Save uploaded file to destination
    
    Args:
        upload_file: FastAPI UploadFile object
        destination: Full path to save the file
        
    Returns:
        str: Path where file was saved
    """
    try:
        with open(destination, "wb") as buffer:
            shutil.copyfileobj(upload_file.file, buffer)
        return destination
    finally:
        upload_file.file.close()


async def save_photo_file(upload_file: UploadFile) -> tuple[str, str, str, str]:
    """
    Save uploaded photo file
    
    Returns:
        tuple: (uuid, original_path, filename, extension)
    """
    # Ensure directories exist
    originals_dir, _ = ensure_upload_dirs()
    
    # Generate unique filename
    photo_uuid, file_extension = generate_unique_filename(upload_file.filename)
    
    # Save original file
    original_filename = f"{photo_uuid}{file_extension}"
    original_path = os.path.join(originals_dir, original_filename)
    
    await save_upload_file(upload_file, original_path)
    
    return photo_uuid, original_path, upload_file.filename, file_extension


def delete_file(file_path: str) -> bool:
    """
    Delete a file if it exists
    
    Returns:
        bool: True if deleted, False if file doesn't exist
    """
    try:
        if os.path.exists(file_path):
            os.remove(file_path)
            return True
        return False
    except Exception:
        return False


def get_file_size(file_path: str) -> Optional[int]:
    """
    Get file size in bytes
    """
    try:
        return os.path.getsize(file_path)
    except Exception:
        return None
