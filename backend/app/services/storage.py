"""
Storage backends for local filesystem and S3-compatible object storage.
"""
import os
import shutil
import tempfile
import uuid
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path
from typing import Iterator, Optional

from fastapi import UploadFile
from fastapi.responses import FileResponse, RedirectResponse, Response

from app.core.config import get_settings

settings = get_settings()

try:
    import boto3
    from botocore.client import Config as BotoConfig
except ModuleNotFoundError:  # pragma: no cover - optional dependency in local mode
    boto3 = None
    BotoConfig = None


@dataclass
class PersistedMedia:
    original_path: str
    thumb_path: Optional[str]
    file_size: Optional[int]


def generate_unique_filename(original_filename: str) -> tuple[str, str]:
    """Generate a stable UUID identifier and preserve extension."""
    file_extension = Path(original_filename).suffix.lower()
    uuid_str = str(uuid.uuid4())
    return uuid_str, file_extension


def ensure_upload_dirs() -> tuple[str, str]:
    """Compatibility helper for local-storage import flows."""
    upload_dir = Path(settings.UPLOAD_DIR)
    originals_dir = upload_dir / "originals"
    thumbnails_dir = upload_dir / "thumbnails"
    originals_dir.mkdir(parents=True, exist_ok=True)
    thumbnails_dir.mkdir(parents=True, exist_ok=True)
    return str(originals_dir), str(thumbnails_dir)


async def save_upload_file(upload_file: UploadFile, destination: str) -> str:
    """Save uploaded file to a temporary or final destination."""
    try:
        with open(destination, "wb") as buffer:
            shutil.copyfileobj(upload_file.file, buffer)
        return destination
    finally:
        upload_file.file.close()


async def stage_photo_upload(upload_file: UploadFile) -> tuple[str, str, str, str]:
    """Persist an uploaded file to a temporary local path for processing."""
    photo_uuid, file_extension = generate_unique_filename(upload_file.filename)
    temp_dir = tempfile.mkdtemp(prefix="buct-media-upload-")
    original_filename = f"{photo_uuid}{file_extension}"
    staged_original_path = os.path.join(temp_dir, original_filename)
    await save_upload_file(upload_file, staged_original_path)
    return photo_uuid, staged_original_path, upload_file.filename, file_extension


class StorageBackend:
    """Base storage backend contract."""

    def persist_photo_files(
        self,
        photo_uuid: str,
        staged_original_path: str,
        staged_thumbnail_path: Optional[str],
    ) -> PersistedMedia:
        raise NotImplementedError

    def delete_file(self, file_path: Optional[str]) -> bool:
        raise NotImplementedError

    def build_media_response(
        self,
        file_path: str,
        download_name: Optional[str] = None,
    ) -> Response:
        raise NotImplementedError

    @contextmanager
    def local_copy(self, file_path: str) -> Iterator[str]:
        raise NotImplementedError


class LocalStorageBackend(StorageBackend):
    """Local filesystem storage backend."""

    def __init__(self) -> None:
        upload_dir = Path(settings.UPLOAD_DIR)
        self.originals_dir = upload_dir / "originals"
        self.thumbnails_dir = upload_dir / "thumbnails"
        self.originals_dir.mkdir(parents=True, exist_ok=True)
        self.thumbnails_dir.mkdir(parents=True, exist_ok=True)

    def _normalize(self, path: str) -> str:
        clean = path.replace("\\", "/")
        if os.path.isabs(clean):
            return clean
        return str((Path(settings.UPLOAD_DIR) / clean).resolve())

    def persist_photo_files(
        self,
        photo_uuid: str,
        staged_original_path: str,
        staged_thumbnail_path: Optional[str],
    ) -> PersistedMedia:
        extension = Path(staged_original_path).suffix.lower()
        original_relative = f"originals/{photo_uuid}{extension}"
        original_target = Path(settings.UPLOAD_DIR) / original_relative
        original_target.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(staged_original_path, original_target)

        thumb_relative = None
        if staged_thumbnail_path:
            thumb_relative = f"thumbnails/{photo_uuid}_thumb.jpg"
            thumb_target = Path(settings.UPLOAD_DIR) / thumb_relative
            thumb_target.parent.mkdir(parents=True, exist_ok=True)
            shutil.move(staged_thumbnail_path, thumb_target)

        return PersistedMedia(
            original_path=original_relative,
            thumb_path=thumb_relative,
            file_size=original_target.stat().st_size if original_target.exists() else None,
        )

    def delete_file(self, file_path: Optional[str]) -> bool:
        if not file_path:
            return False
        try:
            target = self._normalize(file_path)
            if os.path.exists(target):
                os.remove(target)
                return True
            return False
        except Exception:
            return False

    def build_media_response(
        self,
        file_path: str,
        download_name: Optional[str] = None,
    ) -> Response:
        target = self._normalize(file_path)
        return FileResponse(target, filename=download_name)

    @contextmanager
    def local_copy(self, file_path: str) -> Iterator[str]:
        yield self._normalize(file_path)


class S3StorageBackend(StorageBackend):
    """S3-compatible object storage backend."""

    def __init__(self) -> None:
        if boto3 is None or BotoConfig is None:
            raise RuntimeError("boto3 is required for the S3 storage backend.")
        if not all([settings.S3_ENDPOINT, settings.S3_BUCKET, settings.S3_ACCESS_KEY, settings.S3_SECRET_KEY]):
            raise RuntimeError("S3 storage backend requires endpoint, bucket, access key, and secret key.")

        self.bucket = settings.S3_BUCKET
        self.client = boto3.client(
            "s3",
            endpoint_url=settings.S3_ENDPOINT,
            aws_access_key_id=settings.S3_ACCESS_KEY,
            aws_secret_access_key=settings.S3_SECRET_KEY,
            region_name=settings.S3_REGION,
            use_ssl=settings.S3_USE_SSL,
            config=BotoConfig(signature_version="s3v4"),
        )

    def persist_photo_files(
        self,
        photo_uuid: str,
        staged_original_path: str,
        staged_thumbnail_path: Optional[str],
    ) -> PersistedMedia:
        extension = Path(staged_original_path).suffix.lower()
        original_key = f"originals/{photo_uuid}{extension}"
        self.client.upload_file(staged_original_path, self.bucket, original_key)

        thumb_key = None
        if staged_thumbnail_path:
            thumb_key = f"thumbnails/{photo_uuid}_thumb.jpg"
            self.client.upload_file(staged_thumbnail_path, self.bucket, thumb_key)

        size = os.path.getsize(staged_original_path) if os.path.exists(staged_original_path) else None
        return PersistedMedia(original_path=original_key, thumb_path=thumb_key, file_size=size)

    def delete_file(self, file_path: Optional[str]) -> bool:
        if not file_path:
            return False
        try:
            self.client.delete_object(Bucket=self.bucket, Key=file_path)
            return True
        except Exception:
            return False

    def build_media_response(
        self,
        file_path: str,
        download_name: Optional[str] = None,
    ) -> Response:
        params = {"Bucket": self.bucket, "Key": file_path}
        if download_name:
            params["ResponseContentDisposition"] = f'attachment; filename="{download_name}"'
        signed_url = self.client.generate_presigned_url(
            "get_object",
            Params=params,
            ExpiresIn=settings.S3_PRESIGN_EXPIRE_SECONDS,
        )
        return RedirectResponse(signed_url)

    @contextmanager
    def local_copy(self, file_path: str) -> Iterator[str]:
        suffix = Path(file_path).suffix or ".bin"
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as temp_file:
            temp_path = temp_file.name
        self.client.download_file(self.bucket, file_path, temp_path)
        try:
            yield temp_path
        finally:
            if os.path.exists(temp_path):
                os.remove(temp_path)


def cleanup_staged_files(*paths: Optional[str]) -> None:
    """Remove temporary staged files and their temp directories."""
    for path in paths:
        if not path:
            continue
        try:
            if os.path.exists(path):
                os.remove(path)
        except OSError:
            pass
        parent = Path(path).parent
        try:
            if parent.name.startswith("buct-media-upload-") and parent.exists():
                shutil.rmtree(parent, ignore_errors=True)
        except OSError:
            pass


def get_storage_backend() -> StorageBackend:
    """Return the configured storage backend."""
    if settings.STORAGE_BACKEND == "s3":
        return S3StorageBackend()
    return LocalStorageBackend()


def get_storage() -> StorageBackend:
    """Convenience accessor for callers that do not need DI."""
    return get_storage_backend()


def delete_file(file_path: Optional[str]) -> bool:
    """Backward-compatible delete helper."""
    return get_storage().delete_file(file_path)
