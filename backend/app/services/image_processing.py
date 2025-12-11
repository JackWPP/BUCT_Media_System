"""
Image processing service for thumbnails and EXIF extraction
"""
import os
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, Any
from PIL import Image
from PIL.ExifTags import TAGS
from app.core.config import get_settings

settings = get_settings()


def create_thumbnail(
    image_path: str,
    thumb_path: str,
    max_width: int = 400,
    quality: int = 85
) -> tuple[str, int, int]:
    """
    Create thumbnail from image
    
    Args:
        image_path: Path to original image
        thumb_path: Path to save thumbnail
        max_width: Maximum width of thumbnail
        quality: JPEG quality (1-100)
        
    Returns:
        tuple: (thumb_path, thumb_width, thumb_height)
    """
    with Image.open(image_path) as img:
        # Convert to RGB if necessary
        if img.mode in ('RGBA', 'P'):
            img = img.convert('RGB')
        
        # Calculate new dimensions
        width, height = img.size
        if width > max_width:
            ratio = max_width / width
            new_width = max_width
            new_height = int(height * ratio)
        else:
            new_width = width
            new_height = height
        
        # Resize image
        img_resized = img.resize((new_width, new_height), Image.Resampling.LANCZOS)
        
        # Save thumbnail
        img_resized.save(thumb_path, 'JPEG', quality=quality, optimize=True)
        
        return thumb_path, new_width, new_height


def get_image_dimensions(image_path: str) -> tuple[int, int]:
    """
    Get image width and height
    
    Returns:
        tuple: (width, height)
    """
    with Image.open(image_path) as img:
        return img.size


def extract_exif(image_path: str) -> Dict[str, Any]:
    """
    Extract EXIF metadata from image
    
    Returns:
        dict: EXIF data with readable keys
    """
    exif_data = {}
    
    try:
        with Image.open(image_path) as img:
            exif_raw = img._getexif()
            
            if exif_raw:
                for tag_id, value in exif_raw.items():
                    tag = TAGS.get(tag_id, tag_id)
                    
                    # Convert bytes to string
                    if isinstance(value, bytes):
                        try:
                            value = value.decode('utf-8', errors='ignore')
                        except:
                            value = str(value)
                    
                    exif_data[tag] = value
    except Exception as e:
        # If EXIF extraction fails, return empty dict
        pass
    
    return exif_data


def extract_date_taken(exif_data: Dict[str, Any]) -> Optional[datetime]:
    """
    Extract date taken from EXIF data
    
    Args:
        exif_data: EXIF dictionary
        
    Returns:
        datetime or None
    """
    # Try different EXIF date fields
    date_fields = ['DateTimeOriginal', 'DateTime', 'DateTimeDigitized']
    
    for field in date_fields:
        if field in exif_data:
            try:
                date_str = exif_data[field]
                # EXIF date format: "YYYY:MM:DD HH:MM:SS"
                return datetime.strptime(date_str, "%Y:%m:%d %H:%M:%S")
            except:
                continue
    
    return None


def process_uploaded_image(
    original_path: str,
    photo_uuid: str
) -> Dict[str, Any]:
    """
    Process uploaded image: extract EXIF, create thumbnail, get dimensions
    
    Args:
        original_path: Path to original image
        photo_uuid: UUID of the photo
        
    Returns:
        dict: Processing results
    """
    results = {
        'width': None,
        'height': None,
        'thumb_path': None,
        'exif_data': {},
        'captured_at': None
    }
    
    try:
        # Get dimensions
        width, height = get_image_dimensions(original_path)
        results['width'] = width
        results['height'] = height
        
        # Extract EXIF
        exif_data = extract_exif(original_path)
        results['exif_data'] = exif_data
        
        # Extract date taken
        captured_at = extract_date_taken(exif_data)
        results['captured_at'] = captured_at
        
        # Create thumbnail
        upload_dir = Path(settings.UPLOAD_DIR)
        thumbnails_dir = upload_dir / "thumbnails"
        thumbnails_dir.mkdir(parents=True, exist_ok=True)
        
        file_extension = Path(original_path).suffix
        thumb_filename = f"{photo_uuid}_thumb.jpg"
        thumb_path = str(thumbnails_dir / thumb_filename)
        
        create_thumbnail(original_path, thumb_path)
        results['thumb_path'] = thumb_path
        
    except Exception as e:
        # Log error but don't fail
        print(f"Error processing image: {e}")
    
    return results
