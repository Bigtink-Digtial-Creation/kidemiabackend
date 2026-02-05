from pydantic import BaseModel, Field
from typing import Optional
from uuid import UUID


class AccessDeniedDetail(BaseModel):
    allowed: bool = False
    reason: str = Field(..., description="Why access was denied")
    suggestion: Optional[str] = Field(None, description="Action for the user to take")
    method: Optional[str] = Field(
        None, description="Access method: 'wallet' or 'subscription'"
    )
    wallet_balance: Optional[float] = None
    cost: Optional[float] = None
    subscription_id: Optional[UUID] = None


# Global helper for route documentation
ACCESS_RESPONSES = {
    402: {
        "model": AccessDeniedDetail,
        "description": "Subscribe or upgrade to continue using this feature",
    },
    403: {
        "model": AccessDeniedDetail,
        "description": "Feature is not available in current plan",
    },
}
