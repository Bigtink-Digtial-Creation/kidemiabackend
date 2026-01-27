from typing import Optional
from pydantic import BaseModel, EmailStr, Field


class GuardianRegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=8)
    first_name: str
    last_name: str
    relationship_type: Optional[str] = "parent"
    phone_number: Optional[str] = None
