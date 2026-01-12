from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Optional
from src.domains.settings.models.platform_settings import PlatformSetting
from src.domains.settings.schemas.platform_settings import (
    PlatformSettingCreate,
    PlatformSettingUpdate,
    PlatformSettingPublic,
    PlatformSettingResponse,
)

from src.core.security import encrypt_value, get_db, get_current_user_id

router = APIRouter(prefix="/settings", tags=["Platform Settings"])


def mask_secret_value(setting: PlatformSetting) -> PlatformSettingPublic:
    """Mask secret values in response"""
    value = setting.value
    if setting.is_secret and value:
        # Show only first 4 and last 4 characters
        if len(value) > 8:
            value = f"{value[:4]}...{value[-4:]}"
        else:
            value = "***"

    return PlatformSettingPublic(
        id=setting.id,
        key=setting.key,
        value=value,
        category=setting.category,
        description=setting.description,
        is_secret=setting.is_secret,
        is_active=setting.is_active,
        created_at=setting.created_at,
    )


@router.get("/settings", response_model=List[PlatformSettingPublic])
def get_settings(
    category: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user_id),
):
    """Get all platform settings (secrets are masked)"""
    query = db.query(PlatformSetting)

    if category:
        query = query.filter(PlatformSetting.category == category)

    settings = query.all()
    return [mask_secret_value(s) for s in settings]


@router.get("/settings/{setting_id}", response_model=PlatformSettingPublic)
def get_setting(
    setting_id: str,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user_id),
):
    """Get a specific setting"""
    setting = db.query(PlatformSetting).filter(PlatformSetting.id == setting_id).first()

    if not setting:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Setting not found"
        )

    return mask_secret_value(setting)


@router.get("/settings/key/{key}", response_model=PlatformSettingPublic)
def get_setting_by_key(
    key: str, db: Session = Depends(get_db), current_user=Depends(get_current_user_id)
):
    """Get a setting by its key"""
    setting = db.query(PlatformSetting).filter(PlatformSetting.key == key).first()

    if not setting:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Setting not found"
        )

    return mask_secret_value(setting)


@router.post("/settings", response_model=PlatformSettingResponse)
def create_setting(
    setting_in: PlatformSettingCreate,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user_id),
):
    """Create a new platform setting"""
    # Check if key already exists
    existing = (
        db.query(PlatformSetting).filter(PlatformSetting.key == setting_in.key).first()
    )

    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Setting with this key already exists",
        )

    # Encrypt value if it's a secret
    value = setting_in.value
    if setting_in.is_secret and value:
        value = encrypt_value(value)

    setting = PlatformSetting(
        key=setting_in.key,
        value=value,
        category=setting_in.category,
        description=setting_in.description,
        is_secret=setting_in.is_secret,
        is_active=setting_in.is_active,
    )

    db.add(setting)
    db.commit()
    db.refresh(setting)

    return setting


@router.put("/settings/{setting_id}", response_model=PlatformSettingResponse)
def update_setting(
    setting_id: str,
    setting_in: PlatformSettingUpdate,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user_id),
):
    """Update a platform setting"""
    setting = db.query(PlatformSetting).filter(PlatformSetting.id == setting_id).first()

    if not setting:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Setting not found"
        )

    update_data = setting_in.dict(exclude_unset=True)

    # Encrypt value if it's a secret and value is being updated
    if "value" in update_data and setting.is_secret and update_data["value"]:
        update_data["value"] = encrypt_value(update_data["value"])

    for field, value in update_data.items():
        setattr(setting, field, value)

    db.commit()
    db.refresh(setting)

    return setting


@router.delete("/settings/{setting_id}")
def delete_setting(
    setting_id: str,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user_id),
):
    """Delete a platform setting"""
    setting = db.query(PlatformSetting).filter(PlatformSetting.id == setting_id).first()

    if not setting:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Setting not found"
        )

    db.delete(setting)
    db.commit()

    return {"message": "Setting deleted successfully"}


@router.get("/settings/categories/list")
def get_categories(
    db: Session = Depends(get_db), current_user=Depends(get_current_user_id)
):
    """Get list of all setting categories"""
    categories = db.query(PlatformSetting.category).distinct().all()
    return [cat[0] for cat in categories]
