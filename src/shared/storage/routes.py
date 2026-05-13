from fastapi import APIRouter, File, UploadFile, Depends, HTTPException, Query
from pydantic import BaseModel
from typing import Optional
from sqlalchemy.orm import Session
from src.config.database import get_db
from src.shared.storage.exceptions import FileValidationError

# from src.shared.storage.gcs_storage import GCSStorageService, get_storage_service
from src.shared.storage.s3_storage import (
    S3StorageService as GCSStorageService,
    get_storage_service,
)

from src.core.security import get_current_user_id
from src.domains.auth.services.user_service import UserService


router = APIRouter(prefix="/api/upload", tags=["Upload"])


class UploadResponse(BaseModel):
    """Response model for file uploads"""

    success: bool
    url: str
    metadata: dict
    message: str = "File uploaded successfully"


class ErrorResponse(BaseModel):
    """Error response model"""

    success: bool = False
    error: str
    details: Optional[str] = None


@router.patch(
    "/account/avatar",
    response_model=UploadResponse,
    responses={
        400: {"model": ErrorResponse, "description": "Invalid file"},
        500: {"model": ErrorResponse, "description": "Server error"},
    },
    summary="Upload user avatar",
)
async def update_avatar(
    file: UploadFile = File(
        ..., description="File to upload (jpg, png, gif, webp, pdf)"
    ),
    user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db),
    storage: GCSStorageService = Depends(get_storage_service),
):
    """
    Update user avatar with automatic old avatar deletion
    """
    try:
        # Fetch current user

        service = UserService(db)
        current_user = await service.get_user(user_id)

        if not current_user:
            raise HTTPException(status_code=404, detail="User not found")

        # Get old avatar URL
        old_avatar_url = current_user.profile_picture_url

        if old_avatar_url and "storage.googleapis.com" in old_avatar_url:
            try:
                storage.delete_file_by_url(old_avatar_url)
            except Exception as e:
                print(f"Could not delete old avatar: {str(e)}")

        public_url, metadata = storage.upload_file(file, "avatars")

        # await service.update_user(user_id, {"profile_picture_url": public_url})

        return UploadResponse(success=True, url=public_url, metadata=metadata)

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to update avatar: {str(e)}"
        )


@router.post(
    "/questions",
    response_model=UploadResponse,
    summary="Upload question image",
    description="Uploads an image specifically for an assessment question. Stored in 'questions/' folder.",
)
async def upload_question_image(
    file: UploadFile = File(..., description="The question image (jpg, png, webp)"),
    user_id: str = Depends(get_current_user_id),
    storage: GCSStorageService = Depends(get_storage_service),
):
    """
    Focused endpoint for Assessment Question images.
    Enforces the 'questions' folder structure.
    """
    if not file.content_type.startswith("image/"):
        raise HTTPException(
            status_code=400, detail="Question attachments must be images."
        )

    try:
        # Upload using the 'questions' folder prefix
        public_url, metadata = storage.upload_file(file, "questions")

        return UploadResponse(
            success=True,
            url=public_url,
            metadata=metadata,
            message="Question image uploaded successfully",
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post(
    "/badges",
    response_model=UploadResponse,
    summary="Upload badge icon",
    description="Uploads a badge icon. Stored in 'badges/' folder.",
)
async def upload_badge_image(
    file: UploadFile = File(..., description="Badge icon file"),
    user_id: str = Depends(get_current_user_id),
    storage: GCSStorageService = Depends(get_storage_service),
):
    """
    Focused endpoint for Badge icons.
    Enforces the 'badges' folder structure.
    """
    try:
        # Upload using the 'badges' folder prefix
        public_url, metadata = storage.upload_file(file, "badges")

        return UploadResponse(
            success=True,
            url=public_url,
            metadata=metadata,
            message="Badge icon uploaded successfully",
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post(
    "/file",
    response_model=UploadResponse,
    responses={
        400: {"model": ErrorResponse, "description": "Invalid file"},
        500: {"model": ErrorResponse, "description": "Server error"},
    },
    summary="Upload a single file",
    description="Upload a file (image or PDF) to Google Cloud Storage. Maximum file size: 10MB",
)
async def upload_file(
    _: str = Depends(get_current_user_id),
    file: UploadFile = File(
        ..., description="File to upload (jpg, png, gif, webp, pdf)"
    ),
    folder: Optional[str] = Query(
        None,
        description="Optional folder to organize files (e.g., 'questions', 'profiles')",
    ),
    storage: GCSStorageService = Depends(get_storage_service),
    current_user_id: str = Depends(get_current_user_id),
):
    """
    Upload a file to Google Cloud Storage

    - **file**: The file to upload (required)
    - **folder**: Optional folder name for organizing files

    Returns the public URL and metadata
    """
    try:
        public_url, metadata = storage.upload_file(file, folder)
        return UploadResponse(success=True, url=public_url, metadata=metadata)

    except FileValidationError as e:
        raise HTTPException(
            status_code=400,
            detail={
                "success": False,
                "error": "File validation failed",
                "details": str(e),
            },
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail={
                "success": False,
                "error": "Internal server error",
                "details": str(e),
            },
        )


@router.delete(
    "/file",
    summary="Delete a file",
    description="Delete a file from Google Cloud Storage",
)
async def delete_file(
    _: str = Depends(get_current_user_id),
    blob_name: str = Query(..., description="Full path of the file in the bucket"),
    storage: GCSStorageService = Depends(get_storage_service),
):
    """Delete a file from storage"""
    try:
        success = storage.delete_file(blob_name)
        return {"success": success, "message": "File deleted successfully"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail={
                "success": False,
                "error": "Failed to delete file",
                "details": str(e),
            },
        )


@router.get(
    "/file/metadata",
    summary="Get file metadata",
    description="Retrieve metadata for a file",
)
async def get_file_metadata(
    _: str = Depends(get_current_user_id),
    blob_name: str = Query(..., description="Full path of the file in the bucket"),
    storage: GCSStorageService = Depends(get_storage_service),
):
    """Get metadata for a specific file"""
    try:
        metadata = storage.get_file_metadata(blob_name)
        return {"success": True, "metadata": metadata}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail={
                "success": False,
                "error": "Failed to retrieve metadata",
                "details": str(e),
            },
        )
