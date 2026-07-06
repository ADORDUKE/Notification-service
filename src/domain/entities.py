from datetime import datetime
from uuid import UUID
from pydantic import BaseModel, Field, field_validator, EmailStr

class ResetPasswordMessage(BaseModel):
    id: UUID
    user_id: str = Field(..., alias="userId")
    email_address: EmailStr = Field(..., alias="emailAddress")
    subject: str
    body: str
    published_at: datetime = Field(..., alias="publishedAt")
    sent_at: datetime | None = None

# Turn on snake_case and camelCase for import data
model_config = {
    "populate_by_name": True
}

# Add small validation
@field_validator("email_address")
@classmethod
def validate_email(cls, value: str) -> str:
    if "@" not in value:
        raise ValueError("Email address is not valid")
    return value