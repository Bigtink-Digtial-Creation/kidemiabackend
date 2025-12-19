from datetime import datetime
from typing import Optional, Tuple
from pathlib import Path
import uuid
import os
from urllib.parse import urlparse
from fastapi import UploadFile, HTTPException
from google.cloud import storage
from google.cloud.exceptions import GoogleCloudError, NotFound
from src.shared.storage.config import GCSConfig
from src.shared.storage.exceptions import FileValidationError


class GCSStorageService:
    """Service for handling Google Cloud Storage operations"""

    def __init__(self):
        # Determine environment (default to development)
        env = os.getenv("APP_ENV", "development")

        if env == "development":
            # Use local credentials file for dev
            if not GCSConfig.CREDENTIALS_PATH:
                raise ValueError(
                    "GOOGLE_APPLICATION_CREDENTIALS environment variable not set"
                )
            try:
                self.client = storage.Client()
            except GoogleCloudError as e:
                raise ConnectionError(f"Failed to initialize GCS client: {str(e)}")
        else:
            # Production: rely on default credentials (service account, CI/CD env)
            try:
                self.client = storage.Client()
            except GoogleCloudError as e:
                raise ConnectionError(f"Failed to initialize GCS client: {str(e)}")

        self.bucket = self.client.bucket(GCSConfig.BUCKET_NAME)

    def _validate_file_size(self, file: UploadFile) -> None:
        """Validate file size"""
        file.file.seek(0, 2)
        size = file.file.tell()
        file.file.seek(0)

        if size > GCSConfig.MAX_FILE_SIZE:
            raise FileValidationError(
                f"File size ({size / 1024 / 1024:.2f}MB) exceeds maximum allowed "
                f"({GCSConfig.MAX_FILE_SIZE / 1024 / 1024}MB)"
            )

    def _validate_file_extension(self, filename: str) -> None:
        """Validate file extension"""
        ext = Path(filename).suffix.lower()
        if ext not in GCSConfig.ALLOWED_EXTENSIONS:
            raise FileValidationError(
                f"File type '{ext}' not allowed. Allowed types: {', '.join(GCSConfig.ALLOWED_EXTENSIONS)}"
            )

    def _validate_file_content(self, file: UploadFile) -> str:
        """Validate actual file content type using magic bytes"""
        try:
            file.file.seek(0)
            # header = file.file.read(2048)
            file.file.seek(0)

            mime = file.content_type

            if mime not in GCSConfig.ALLOWED_MIME_TYPES:
                raise FileValidationError(
                    f"File content type '{mime}' not allowed. This might be a malicious file."
                )

            return mime
        except Exception as e:
            raise FileValidationError(f"Failed to validate file content: {str(e)}")

    def _generate_unique_filename(self, original_filename: str) -> str:
        """Generate a unique filename with timestamp and UUID"""
        ext = Path(original_filename).suffix.lower()
        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        unique_id = str(uuid.uuid4())[:8]

        base_name = Path(original_filename).stem
        safe_name = "".join(c for c in base_name if c.isalnum() or c in ("-", "_"))[:30]

        return f"{timestamp}_{unique_id}_{safe_name}{ext}"

    def extract_blob_name_from_url(self, url: str) -> Optional[str]:
        """
        Extract blob name from GCS public URL

        Examples:
        - https://storage.googleapis.com/kidemia-bucket/avatars/20241219_abc123_profile.jpg
          -> avatars/20241219_abc123_profile.jpg
        - https://storage.googleapis.com/kidemia-bucket/questions/image.png
          -> questions/image.png
        """
        if not url:
            return None

        try:
            # Parse the URL
            parsed = urlparse(url)

            # Check if it's a GCS URL
            if "storage.googleapis.com" not in parsed.netloc:
                return None

            path = parsed.path.lstrip("/")

            # Remove bucket name from path
            # Path format: bucket-name/folder/filename
            parts = path.split("/", 1)
            if len(parts) > 1:
                return parts[1]  # Return folder/filename

            return None
        except Exception as e:
            print(f"Error extracting blob name from URL: {str(e)}")
            return None

    def delete_file_by_url(self, url: str) -> bool:
        """
        Delete a file using its public URL

        Args:
            url: The public GCS URL

        Returns:
            True if deleted successfully, False if file not found
        """
        blob_name = self.extract_blob_name_from_url(url)

        if not blob_name:
            print(f"Could not extract blob name from URL: {url}")
            return False

        return self.delete_file(blob_name)

    def upload_file(
        self, file: UploadFile, folder: Optional[str] = None
    ) -> Tuple[str, dict]:
        """
        Upload file to Google Cloud Storage with validation

        Args:
            file: The file to upload
            folder: Optional folder/prefix for organizing files

        Returns:
            Tuple of (public_url, metadata)
        """
        if not file or not file.filename:
            raise FileValidationError("No file provided")

        try:
            self._validate_file_extension(file.filename)
            self._validate_file_size(file)
            actual_mime_type = self._validate_file_content(file)

            unique_filename = self._generate_unique_filename(file.filename)

            if folder:
                blob_name = f"{folder}/{unique_filename}"
            else:
                blob_name = unique_filename

            blob = self.bucket.blob(blob_name)
            blob.content_type = actual_mime_type
            blob.cache_control = "public, max-age=31536000"

            file.file.seek(0)
            blob.upload_from_file(file.file, content_type=actual_mime_type, timeout=60)

            public_url = (
                f"https://storage.googleapis.com/{GCSConfig.BUCKET_NAME}/{blob_name}"
            )

            metadata = {
                "original_filename": file.filename,
                "stored_filename": blob_name,
                "size_bytes": blob.size,
                "content_type": actual_mime_type,
                "uploaded_at": datetime.utcnow().isoformat(),
                "url": public_url,
            }

            return public_url, metadata

        except FileValidationError:
            raise
        except GoogleCloudError as e:
            raise HTTPException(
                status_code=500, detail=f"Failed to upload file to storage: {str(e)}"
            )
        except Exception as e:
            raise HTTPException(
                status_code=500, detail=f"Unexpected error during file upload: {str(e)}"
            )

    def delete_file(self, blob_name: str) -> bool:
        """
        Delete a file from GCS

        Args:
            blob_name: The name of the blob to delete (path in bucket)

        Returns:
            True if deleted successfully, False if not found
        """
        try:
            blob = self.bucket.blob(blob_name)
            blob.delete()
            print(f"Successfully deleted: {blob_name}")
            return True
        except NotFound:
            print(f"File not found: {blob_name}")
            return False
        except GoogleCloudError as e:
            print(f"Error deleting file: {str(e)}")
            raise HTTPException(
                status_code=500, detail=f"Failed to delete file: {str(e)}"
            )

    def get_file_metadata(self, blob_name: str) -> dict:
        """Get metadata for a file"""
        try:
            blob = self.bucket.blob(blob_name)
            blob.reload()

            return {
                "name": blob.name,
                "size_bytes": blob.size,
                "content_type": blob.content_type,
                "created_at": blob.time_created.isoformat()
                if blob.time_created
                else None,
                "updated_at": blob.updated.isoformat() if blob.updated else None,
                "public_url": blob.public_url,
            }
        except GoogleCloudError as e:
            raise HTTPException(status_code=404, detail=f"File not found: {str(e)}")


_storage_service: Optional[GCSStorageService] = None


def get_storage_service() -> GCSStorageService:
    """Dependency injection for storage service"""
    global _storage_service
    if _storage_service is None:
        _storage_service = GCSStorageService()
    return _storage_service
