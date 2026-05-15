"""
Image processing service for thumbnails, compression, and EXIF extraction
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
    max_width: int = 800,
    quality: int = 80,
    max_size_bytes: int = 1024 * 1024,  # 1MB
) -> tuple[str, int, int]:
    """
    Create thumbnail with center crop, capped at max_size_bytes.
    Landscape → 3:2 crop, Portrait → 2:3 crop, Square → 3:2 crop.

    Args:
        image_path: Path to original image
        thumb_path: Path to save thumbnail
        max_width: Maximum width of thumbnail
        quality: Initial JPEG quality (1-100)
        max_size_bytes: Maximum file size

    Returns:
        tuple: (thumb_path, thumb_width, thumb_height)
    """

    with Image.open(image_path) as img:
        if img.mode in ('RGBA', 'P'):
            img = img.convert('RGB')

        w, h = img.size

        # Determine crop ratio based on orientation
        if h > w:
            # Portrait → 2:3 (width:height)
            target_ratio = 2 / 3
        else:
            # Landscape or square → 3:2 (width:height)
            target_ratio = 3 / 2

        # Center crop to target ratio
        current_ratio = w / h
        if current_ratio > target_ratio:
            # Wider than target → crop sides
            new_w = int(h * target_ratio)
            left = (w - new_w) // 2
            img = img.crop((left, 0, left + new_w, h))
        elif current_ratio < target_ratio:
            # Taller than target → crop top/bottom
            new_h = int(w / target_ratio)
            top = (h - new_h) // 2
            img = img.crop((0, top, w, top + new_h))

        # Resize: landscape → max_width on width, portrait → max_width on height
        crop_w, crop_h = img.size
        if crop_h > crop_w:
            # Portrait: constrain height to max_width (so cards are same height)
            if crop_h > max_width:
                ratio = max_width / crop_h
                new_h = max_width
                new_w = int(crop_w * ratio)
                img = img.resize((new_w, new_h), Image.Resampling.LANCZOS)
        else:
            # Landscape: constrain width to max_width
            if crop_w > max_width:
                ratio = max_width / crop_w
                new_w = max_width
                new_h = int(crop_h * ratio)
                img = img.resize((new_w, new_h), Image.Resampling.LANCZOS)

        # Save with quality fallback to hit size target
        for q in (quality, 70, 60, 50):
            img.save(thumb_path, 'JPEG', quality=q, optimize=True)
            size = os.path.getsize(thumb_path)
            if size <= max_size_bytes:
                break

        final_w, final_h = img.size
        return thumb_path, final_w, final_h


def create_compressed(
    image_path: str,
    compressed_path: str,
    max_size_bytes: int = 5 * 1024 * 1024,  # 5MB
) -> tuple[str, int, int, int]:
    """
    Create a compressed version of the image capped at max_size_bytes.

    Strategy:
    1. Keep original dimensions, lower JPEG quality from 85 down to 60
    2. If still too large, progressively reduce long edge by 10%
    3. Never go below quality=50 or long edge 1600px

    Returns:
        tuple: (compressed_path, width, height, file_size_bytes)
    """
    with Image.open(image_path) as img:
        if img.mode in ('RGBA', 'P'):
            img = img.convert('RGB')

        orig_w, orig_h = img.size
        w, h = orig_w, orig_h

        # Phase 1: lower quality at original dimensions
        for quality in (85, 75, 65, 60):
            img.save(compressed_path, 'JPEG', quality=quality, optimize=True)
            size = os.path.getsize(compressed_path)
            if size <= max_size_bytes:
                return compressed_path, w, h, size

        # Phase 2: reduce dimensions
        for scale in (0.9, 0.8, 0.7, 0.6, 0.5):
            new_w = max(int(orig_w * scale), 1600)
            new_h = max(int(orig_h * scale), int(1600 * orig_h / orig_w))
            if new_w >= w and new_h >= h:
                continue  # already tried this size or larger
            w, h = new_w, new_h
            img_resized = img.resize((w, h), Image.Resampling.LANCZOS)
            img_resized.save(compressed_path, 'JPEG', quality=60, optimize=True)
            size = os.path.getsize(compressed_path)
            if size <= max_size_bytes:
                return compressed_path, w, h, size

        # Last resort: force to 1600px long edge, quality 50
        ratio = 1600 / max(orig_w, orig_h)
        w, h = int(orig_w * ratio), int(orig_h * ratio)
        img_resized = img.resize((w, h), Image.Resampling.LANCZOS)
        img_resized.save(compressed_path, 'JPEG', quality=50, optimize=True)
        size = os.path.getsize(compressed_path)
        return compressed_path, w, h, size


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
        dict: EXIF data with readable keys (JSON-serializable)
    """
    exif_data = {}
    
    try:
        with Image.open(image_path) as img:
            exif_raw = img._getexif()
            
            if exif_raw:
                for tag_id, value in exif_raw.items():
                    tag = TAGS.get(tag_id, tag_id)
                    
                    # 处理特殊类型以保证JSON可序列化
                    # Convert bytes to string
                    if isinstance(value, bytes):
                        try:
                            value = value.decode('utf-8', errors='ignore')
                        except:
                            value = str(value)
                    # Convert IFDRational to float
                    elif hasattr(value, '__class__') and value.__class__.__name__ == 'IFDRational':
                        try:
                            value = float(value)
                        except:
                            value = str(value)
                    # Convert tuple of IFDRational to list of float
                    elif isinstance(value, tuple):
                        try:
                            value = [
                                float(v) if hasattr(v, '__class__') and v.__class__.__name__ == 'IFDRational' else v
                                for v in value
                            ]
                        except:
                            value = str(value)
                    # Convert other non-serializable types
                    elif not isinstance(value, (str, int, float, bool, list, dict, type(None))):
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
    photo_uuid: str,
    output_dir: Optional[str] = None,
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
        'compressed_path': None,
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
        thumbnails_dir = Path(output_dir) if output_dir else (Path(settings.UPLOAD_DIR) / "thumbnails")
        thumbnails_dir.mkdir(parents=True, exist_ok=True)

        thumb_filename = f"{photo_uuid}_thumb.jpg"
        thumb_path = str(thumbnails_dir / thumb_filename)
        
        create_thumbnail(original_path, thumb_path)
        results['thumb_path'] = thumb_path

        # Create compressed version (skip if original is already ≤ 5MB)
        original_size = os.path.getsize(original_path)
        if original_size > 5 * 1024 * 1024:
            compressed_filename = f"{photo_uuid}_compressed.jpg"
            compressed_path = str(thumbnails_dir / compressed_filename)
            create_compressed(original_path, compressed_path)
            results['compressed_path'] = compressed_path
        
    except Exception as e:
        # Log error but don't fail
        print(f"Error processing image: {e}")
    
    return results
