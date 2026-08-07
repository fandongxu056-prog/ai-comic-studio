"""File storage service — S3/MinIO abstraction layer."""

from io import BytesIO
from typing import Optional

from minio import Minio
from minio.error import S3Error

from app.config import settings


class FileService:
    """Manages file uploads/downloads via S3-compatible storage (MinIO)."""

    def __init__(self):
        self.client = Minio(
            endpoint=settings.s3_endpoint,
            access_key=settings.s3_access_key,
            secret_key=settings.s3_secret_key,
            secure=settings.s3_secure,
        )
        self.bucket = settings.s3_bucket
        self._ensure_bucket()

    def _ensure_bucket(self) -> None:
        """Create bucket if it does not exist."""
        if not self.client.bucket_exists(self.bucket):
            self.client.make_bucket(self.bucket)

    async def upload(self, object_name: str, data: bytes, content_type: str = "application/octet-stream") -> str:
        """Upload a file and return its public URL."""
        self.client.put_object(
            bucket_name=self.bucket,
            object_name=object_name,
            data=BytesIO(data),
            length=len(data),
            content_type=content_type,
        )
        return f"{settings.s3_public_url}/{object_name}"

    async def download(self, object_name: str) -> Optional[bytes]:
        """Download a file as bytes."""
        try:
            response = self.client.get_object(self.bucket, object_name)
            return response.read()
        except S3Error:
            return None

    async def delete(self, object_name: str) -> bool:
        """Delete a file. Returns True if successful."""
        try:
            self.client.remove_object(self.bucket, object_name)
            return True
        except S3Error:
            return False

    async def get_presigned_url(self, object_name: str, expires_seconds: int = 3600) -> str:
        """Generate a presigned download URL."""
        return self.client.presigned_get_object(
            bucket_name=self.bucket,
            object_name=object_name,
            expires=expires_seconds,
        )


# Singleton
file_service = FileService()
