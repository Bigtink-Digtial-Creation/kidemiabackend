from datetime import datetime
from typing import Optional, Tuple
from pathlib import Path
import uuid
from urllib.parse import urlparse
from fastapi import UploadFile, HTTPException
import boto3
from botocore.exceptions import ClientError
from src.shared.storage.s3_config import S3Config
from src.shared.storage.exceptions import FileValidationError


class S3StorageService:
    """S3-compatible storage service for Contabo Object Storage"""

    def __init__(self):
        self.client = boto3.client(
            "s3",
            endpoint_url=S3Config.ENDPOINT_URL,
            aws_access_key_id=S3Config.ACCESS_KEY,
            aws_secret_access_key=S3Config.SECRET_KEY,
        )
        self.bucket_name = S3Config.BUCKET_NAME

    def _validate_file_size(self, file: UploadFile) -> None:
        file.file.seek(0, 2)
        size = file.file.tell()
        file.file.seek(0)
        if size > S3Config.MAX_FILE_SIZE:
            raise FileValidationError(
                f"File size ({size / 1024 / 1024:.2f}MB) exceeds maximum allowed "
                f"({S3Config.MAX_FILE_SIZE / 1024 / 1024}MB)"
            )

    def _validate_file_extension(self, filename: str) -> None:
        ext = Path(filename).suffix.lower()
        if ext not in S3Config.ALLOWED_EXTENSIONS:
            raise FileValidationError(
                f"File type '{ext}' not allowed. Allowed types: {', '.join(S3Config.ALLOWED_EXTENSIONS)}"
            )

    def _validate_file_content(self, file: UploadFile) -> str:
        file.file.seek(0)
        mime = file.content_type
        if mime not in S3Config.ALLOWED_MIME_TYPES:
            raise FileValidationError(f"File content type '{mime}' not allowed.")
        file.file.seek(0)
        return mime

    def _generate_unique_filename(self, original_filename: str) -> str:
        ext = Path(original_filename).suffix.lower()
        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        unique_id = str(uuid.uuid4())[:8]
        base_name = Path(original_filename).stem
        safe_name = "".join(c for c in base_name if c.isalnum() or c in ("-", "_"))[:30]
        return f"{timestamp}_{unique_id}_{safe_name}{ext}"

    def extract_blob_name_from_url(self, url: str) -> Optional[str]:
        if not url:
            return None
        try:
            parsed = urlparse(url)
            path = parsed.path.lstrip("/")
            # Path format: bucket-name/folder/filename
            parts = path.split("/", 1)
            if len(parts) > 1:
                return parts[1]
            return None
        except Exception as e:
            print(f"Error extracting blob name from URL: {str(e)}")
            return None

    def delete_file_by_url(self, url: str) -> bool:
        blob_name = self.extract_blob_name_from_url(url)
        if not blob_name:
            print(f"Could not extract blob name from URL: {url}")
            return False
        return self.delete_file(blob_name)

    def upload_file(
        self, file: UploadFile, folder: Optional[str] = None
    ) -> Tuple[str, dict]:
        if not file or not file.filename:
            raise FileValidationError("No file provided")

        try:
            self._validate_file_extension(file.filename)
            self._validate_file_size(file)
            actual_mime_type = self._validate_file_content(file)

            unique_filename = self._generate_unique_filename(file.filename)
            blob_name = f"{folder}/{unique_filename}" if folder else unique_filename

            file.file.seek(0)
            self.client.upload_fileobj(
                file.file,
                self.bucket_name,
                blob_name,
                ExtraArgs={
                    "ContentType": actual_mime_type,
                    "ACL": "public-read",
                    "CacheControl": "public, max-age=31536000",
                },
            )

            # public_url = f"{S3Config.ENDPOINT_URL}/{S3Config.TENANT_ID}:{self.bucket_name}/{blob_name}"
            public_url = f"{S3Config.ENDPOINT_URL}/{S3Config.TENANT_ID}:{self.bucket_name}/{blob_name}"

            metadata = {
                "original_filename": file.filename,
                "stored_filename": blob_name,
                "size_bytes": file.file.seek(0, 2),
                "content_type": actual_mime_type,
                "uploaded_at": datetime.utcnow().isoformat(),
                "url": public_url,
            }

            return public_url, metadata

        except FileValidationError:
            raise
        except ClientError as e:
            raise HTTPException(
                status_code=500, detail=f"Failed to upload file: {str(e)}"
            )
        except Exception as e:
            raise HTTPException(
                status_code=500, detail=f"Unexpected error during upload: {str(e)}"
            )

    def delete_file(self, blob_name: str) -> bool:
        try:
            self.client.delete_object(Bucket=self.bucket_name, Key=blob_name)
            print(f"Successfully deleted: {blob_name}")
            return True
        except ClientError as e:
            if e.response["Error"]["Code"] == "NoSuchKey":
                print(f"File not found: {blob_name}")
                return False
            raise HTTPException(
                status_code=500, detail=f"Failed to delete file: {str(e)}"
            )

    def get_file_metadata(self, blob_name: str) -> dict:
        try:
            response = self.client.head_object(Bucket=self.bucket_name, Key=blob_name)
            return {
                "name": blob_name,
                "size_bytes": response["ContentLength"],
                "content_type": response["ContentType"],
                "created_at": None,
                "updated_at": response["LastModified"].isoformat(),
                "public_url": f"{S3Config.ENDPOINT_URL}/{self.bucket_name}/{blob_name}",
            }
        except ClientError as e:
            raise HTTPException(status_code=404, detail=f"File not found: {str(e)}")


_storage_service: Optional[S3StorageService] = None


def get_storage_service() -> S3StorageService:
    global _storage_service
    if _storage_service is None:
        _storage_service = S3StorageService()
    return _storage_service
